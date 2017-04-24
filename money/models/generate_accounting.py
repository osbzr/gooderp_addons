# -*- coding: utf-8 -*-
# ##############################################################################
#
#    Copyright (C) 2016  开阖软件(<http://www.osbzr.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError


class money_order(models.Model):
    _inherit = 'money.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict',
                                 help=u'收付款单审核时生成的对应凭证')

    @api.multi
    def money_order_done(self):
        """
        审核收入款单，生成凭证并审核
        :return: 
        """
        res = super(money_order, self).money_order_done()
        for money in self:
            if money.type == 'get':
                voucher = money.create_money_order_get_voucher(money.line_ids, money.source_ids, money.partner_id, money.name, money.note or '')
            else:
                voucher = money.create_money_order_pay_voucher(money.line_ids, money.source_ids, money.partner_id, money.name, money.note or '')
            voucher.voucher_done()
        return res

    @api.multi
    def money_order_draft(self):
        """
        反审核收付款单，反审核凭证并删除
        :return: 
        """
        res = super(money_order, self).money_order_draft()
        for money in self:
            voucher, money.voucher_id = money.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            voucher.unlink()
        return res

    def _prepare_vouch_line_data(self, line, name, account_id, debit, credit, voucher_id, partner_id, currency_id):
        rate_silent = currency_amount = 0
        if currency_id:
            rate_silent = self.env['res.currency'].get_rate_silent(self.date, currency_id)
            currency_amount = debit or credit
            debit = debit * (rate_silent or 1)
            credit = credit * (rate_silent or 1)
        return {
                'name': name,
                'account_id': account_id,
                'debit': debit,
                'credit': credit,
                'voucher_id': voucher_id,
                'partner_id': partner_id,
                'currency_id': currency_id,
                'currency_amount': currency_amount,
                'rate_silent':rate_silent or ''
                }

    def _create_voucher_line(self, line, name, account_id, debit, credit, voucher_id, partner_id, currency_id):
        line_data = self._prepare_vouch_line_data(line, name, account_id, debit, credit, voucher_id, partner_id, currency_id)
        voucher_line = self.env['voucher.line'].create(line_data)
        return voucher_line

    @api.multi
    def create_money_order_get_voucher(self, line_ids, source_ids, partner, name, note):
        """
        为收款单创建凭证
        :param line_ids: 收款单明细
        :param source_ids: 没用到
        :param partner: 客户
        :param name: 收款单名称
        :return: 创建的凭证
        """
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})
        amount_all = 0.0
        for line in line_ids:
            if not line.bank_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (line.bank_id.name))
            # 生成借方明细行
            # param: line, name, account_id, debit, credit, voucher_id, partner_id
            self._create_voucher_line(line,
                                     u"%s %s" % (name, note),
                                     line.bank_id.account_id.id,
                                     line.amount,
                                     0,
                                     vouch_obj.id,
                                     '',
                                     line.currency_id.id
                                     )

            amount_all += line.amount
        if self.discount_amount != 0:
            # 生成借方明细行
            # param: False, name, account_id, debit, credit, voucher_id, partner_id
            self._create_voucher_line(False,
                                     u"%s 现金折扣 %s" % (name, note),
                                     self.discount_account_id.id,
                                     self.discount_amount,
                                     0,
                                     vouch_obj.id,
                                     self.partner_id.id,
                                     line.currency_id.id
                                     )

        if partner.c_category_id:
            partner_account_id = partner.c_category_id.account_id.id

        # 生成贷方明细行
        # param: source, name, account_id, debit, credit, voucher_id, partner_id
        self._create_voucher_line('',
                                  u"%s %s" % (name, note),
                                  partner_account_id,
                                  0,
                                  amount_all + self.discount_amount,
                                  vouch_obj.id,
                                  self.partner_id.id,
                                  line.currency_id.id
                                  )
        return vouch_obj

    @api.multi
    def create_money_order_pay_voucher(self, line_ids, source_ids, partner, name, note):
        """
        为付款单创建凭证
        :param line_ids: 付款单明细
        :param source_ids: 没用到
        :param partner: 供应商
        :param name: 付款单名称
        :return: 创建的凭证
        """
        vouch_obj = self.env['voucher'].create({'date': self.date})
        self.write({'voucher_id': vouch_obj.id})

        amount_all = 0.0
        for line in line_ids:
            if not line.bank_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (line.bank_id.name))
            # 生成贷方明细行 credit
            # param: line, name, account_id, debit, credit, voucher_id, partner_id
            self._create_voucher_line(line,
                                      u"%s %s" % (name, note),
                                      line.bank_id.account_id.id,
                                      0,
                                      line.amount,
                                      vouch_obj.id,
                                      '',
                                      line.currency_id.id
                                      )
            amount_all += line.amount
        partner_account_id = partner.s_category_id.account_id.id

        # 生成借方明细行 debit
        # param: source, name, account_id, debit, credit, voucher_id, partner_id
        self._create_voucher_line('',
                                  u"%s %s" % (name, note),
                                  partner_account_id,
                                  amount_all - self.discount_amount,
                                  0,
                                  vouch_obj.id,
                                  self.partner_id.id,
                                  line.currency_id.id
                                  )

        if self.discount_amount != 0:
            # 生成借方明细行 debit
            # param: False, name, account_id, debit, credit, voucher_id, partner_id
            self._create_voucher_line(line,
                                      u"%s 手续费 %s" % (name, note),
                                      self.discount_account_id.id,
                                      self.discount_amount,
                                      0,
                                      vouch_obj.id,
                                      self.partner_id.id,
                                      line.currency_id.id
                                      )
        return vouch_obj


class money_invoice(models.Model):
    _inherit = 'money.invoice'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict',
                                 help=u'结算单审核时生成的对应凭证')

    @api.multi
    def money_invoice_draft(self):
        """
        反审核结算单时，反审核凭证
        :return: 
        """
        res = super(money_invoice, self).money_invoice_draft()
        for invoice in self:
            voucher, invoice.voucher_id = invoice.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            # 始初化单反审核只删除明细行：生成初始化凭证时，不生成往来单位对方的科目，所以要删除相关明细行
            if invoice.is_init:
                vouch_obj = self.env['voucher'].search([('id', '=', voucher.id)])
                vouch_obj_lines = self.env['voucher.line'].search([
                    ('voucher_id', '=', vouch_obj.id),
                    ('partner_id', '=', invoice.partner_id.id),
                    ('init_obj', '=', 'money_invoice'), ])
                for vouch_obj_line in vouch_obj_lines:
                    vouch_obj_line.unlink()
            else:   # 非初始化单反审核时删除凭证
                voucher.unlink()
        return res

    @api.multi
    def money_invoice_done(self):
        """
        审核结算单时，创建凭证并审核
        :return: 
        """
        res = super(money_invoice, self).money_invoice_done()
        vals = {}
        # 初始化单的话，先找是否有初始化凭证，没有则新建一个
        for invoice in self:
            if invoice.is_init:
                vouch_obj = self.env['voucher'].search([('is_init', '=', True)])
                if not vouch_obj:
                    vouch_obj = self.env['voucher'].create({'date': invoice.date})
                invoice.write({'voucher_id': vouch_obj.id})
                vouch_obj.is_init = True
            else:
                vouch_obj = self.env['voucher'].create({'date': invoice.date})
                invoice.write({'voucher_id': vouch_obj.id})
            if not invoice.category_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (invoice.category_id.name))
            partner_cat = invoice.category_id.type == 'income' and invoice.partner_id.c_category_id or invoice.partner_id.s_category_id
            partner_account_id = partner_cat.account_id.id
            if not partner_account_id:
                raise UserError(u'请配置%s的会计科目' % (partner_cat.name))
            if invoice.category_id.type == 'income':
                vals.update({'vouch_obj_id': vouch_obj.id, 'partner_credit': invoice.partner_id.id, 'name': invoice.name, 'string': invoice.note or '',
                             'amount': invoice.amount, 'credit_account_id': invoice.category_id.account_id.id, 'partner_debit': invoice.partner_id.id,
                             'debit_account_id': partner_account_id, 'sell_tax_amount': invoice.tax_amount or 0,
                             'credit_auxiliary_id':invoice.auxiliary_id.id, 'currency_id':invoice.currency_id.id or '',
                             'rate_silent':self.env['res.currency'].get_rate_silent(self.date, invoice.currency_id.id) or 0,
                             })
            else:
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': invoice.name, 'string': invoice.note or '',
                             'amount': invoice.amount, 'credit_account_id': partner_account_id,
                             'debit_account_id': invoice.category_id.account_id.id, 'partner_debit': invoice.partner_id.id,
                             'partner_credit':invoice.partner_id.id, 'buy_tax_amount': invoice.tax_amount or 0,
                             'debit_auxiliary_id':invoice.auxiliary_id.id, 'currency_id':invoice.currency_id.id or '',
                             'rate_silent':self.env['res.currency'].get_rate_silent(self.date, invoice.currency_id.id) or 0,
                             })
            if invoice.is_init:
                vals.update({'init_obj': 'money_invoice', })
            invoice.create_voucher_line(vals)

            '''
TODO：这段代码未经严格测试验证，暂时注释掉 -- jeff 2017-3-4
            # 如果为采购或销售，则生成凭证后删除统一的凭证行，按出入库内容明细行生成
            if invoice.category_id.type in ('expense','income'):
                vouch_line_ids = self.env['voucher.line'].search([
                    ('account_id', '=', invoice.category_id.account_id.id),
                    ('voucher_id', '=', vouch_obj.id)])
                for vouch_line_id in vouch_line_ids:
                    vouch_line_id.unlink()
                wh_move = self.env['wh.move'].search([
                    ('name', '=', invoice.name)])
                for wh_move_line in wh_move.line_out_ids:
                    self.env['voucher.line'].create({
                        'name': u"销售%s" % (wh_move_line.goods_id.name),
                        'account_id': wh_move_line.goods_id.category_id.account_out_id.id,
                        'credit': wh_move_line.amount * vals.get('rate_silent'),
                        'voucher_id': vouch_obj.id,
                        'auxiliary_id':vals.get('debit_auxiliary_id', False),
                        'currency_id':vals.get('currency_id'),
                        'currency_amount': wh_move_line.amount,
                        'rate_silent':vals.get('rate_silent'),
                        'init_obj':False,
                        })
                for wh_move_line in wh_move.line_in_ids:
                    self.env['voucher.line'].create({
                        'name': u"采购%s" % (wh_move_line.goods_id.name),
                        'account_id': wh_move_line.goods_id.category_id.account_in_id.id,
                        'debit': wh_move_line.cost,
                        'voucher_id': vouch_obj.id,
                        'auxiliary_id':vals.get('debit_auxiliary_id', False),
                        'init_obj':False,
                        })
            '''
            # 删除初始非需要的凭证明细行,不审核凭证
            if invoice.is_init:
                vouch_line_ids = self.env['voucher.line'].search([
                    ('account_id', '=', invoice.category_id.account_id.id),
                    ('init_obj', '=', 'money_invoice')])
                for vouch_line_id in vouch_line_ids:
                    vouch_line_id.unlink()
            else:
                vouch_obj.voucher_done()
        return res

    @api.multi
    def create_voucher_line(self, vals):
        if vals.get('currency_id') == self.env.user.company_id.currency_id.id or not vals.get('rate_silent'):
            debit = credit = vals.get('amount')
            sell_tax_amount = vals.get('sell_tax_amount')
        else:
            # 外币免税
            debit = credit = vals.get('amount') * vals.get('rate_silent')
        # 把税从金额中减去
        if vals.get('buy_tax_amount'):  # 如果传入了进项税
            debit = vals.get('amount') - vals.get('buy_tax_amount')
        if vals.get('sell_tax_amount'): # 如果传入了销项税
            credit = vals.get('amount') - sell_tax_amount
        # 借方行
        currency_id = vals.get('currency_id') or self.env.user.company_id.currency_id.id
        if currency_id != self.env.user.company_id.currency_id.id:  # 结算单上是外币
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': vals.get('debit_account_id'),
                'debit': debit,
                'voucher_id': vals.get('vouch_obj_id'),
                'partner_id': vals.get('partner_debit', ''),
                'auxiliary_id':vals.get('debit_auxiliary_id', False),
                'currency_id':vals.get('currency_id'),
                'currency_amount': vals.get('amount'),
                'rate_silent':vals.get('rate_silent'),
                'init_obj':vals.get('init_obj', False),
            })
        else:   # 结算单上是本位币
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': vals.get('debit_account_id'),
                'debit': debit,
                'voucher_id': vals.get('vouch_obj_id'),
                'partner_id': vals.get('partner_debit', ''),
                'auxiliary_id':vals.get('debit_auxiliary_id', False),
                'init_obj':vals.get('init_obj', False),
            })
        # 进项税行
        if vals.get('buy_tax_amount'):
            if not self.env.user.company_id.import_tax_account:
                raise UserError(u'请通过"配置-->高级配置-->公司"菜单来设置进项税科目')
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': self.env.user.company_id.import_tax_account.id, 'debit': vals.get('buy_tax_amount'), 'voucher_id': vals.get('vouch_obj_id'),
            })
        # 贷方行
        currency_id = vals.get('currency_id') or self.env.user.company_id.currency_id.id
        if currency_id != self.env.user.company_id.currency_id.id:
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'partner_id': vals.get('partner_credit', ''),
                'account_id': vals.get('credit_account_id'),
                'credit': credit,
                'voucher_id': vals.get('vouch_obj_id'),
                'auxiliary_id':vals.get('credit_auxiliary_id', False),
                'currency_amount': vals.get('amount'),
                'rate_silent':vals.get('rate_silent'), 'currency_id':vals.get('currency_id'),
                'init_obj':vals.get('init_obj', False),
            })
        else:
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'partner_id': vals.get('partner_credit', ''),
                'account_id': vals.get('credit_account_id'),
                'credit': credit,
                'voucher_id': vals.get('vouch_obj_id'),
                'auxiliary_id':vals.get('credit_auxiliary_id', False),
                'init_obj':vals.get('init_obj', False),
            })
        # 销项税行
        if vals.get('sell_tax_amount'):
            if not self.env.user.company_id.output_tax_account:            
                raise UserError(u'您还没有配置公司的销项税科目。\n请通过"配置-->高级配置-->公司"菜单来设置销项税科目!')
            self.env['voucher.line'].create({
                'name': u"%s %s" % (vals.get('name'), vals.get('string')),
                'account_id': self.env.user.company_id.output_tax_account.id, 'credit': sell_tax_amount, 'voucher_id': vals.get('vouch_obj_id'),
        })

        return True


class other_money_order(models.Model):
    _inherit = 'other.money.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict',
                                 help=u'其他收支单审核时生成的对应凭证')

    @api.multi
    def other_money_draft(self):
        """
        反审核其他收支单，反审核凭证
        :return: 
        """
        res = super(other_money_order, self).other_money_draft()
        for money_order in self:
            voucher, money_order.voucher_id = money_order.voucher_id, False
            if voucher.state == 'done':
                voucher.voucher_draft()
            # 始初化单反审核只删除明细行
            if money_order.is_init:
                vouch_obj = self.env['voucher'].search([('id', '=', voucher.id)])
                vouch_obj_lines = self.env['voucher.line'].search([
                    ('voucher_id', '=', vouch_obj.id),
                    ('account_id', '=', money_order.bank_id.account_id.id),
                    ('init_obj', '=', 'other_money_order-%s' % (money_order.id))])
                for vouch_obj_line in vouch_obj_lines:
                    vouch_obj_line.unlink()
            else:
                voucher.unlink()
        return res

    @api.multi
    def other_money_done(self):
        """
        审核其他收支单，创建凭证并审核非初始化凭证
        :return: 
        """
        self.ensure_one()
        res = super(other_money_order, self).other_money_done()
        for money_order in self:
            vals = {}
            # 初始化单的话，先找是否有初始化凭证，没有则新建一个
            if money_order.is_init:
                vouch_obj = self.env['voucher'].search([('is_init', '=', True)])
                if not vouch_obj:
                    vouch_obj = self.env['voucher'].create({'date': money_order.date})
                money_order.write({'voucher_id': vouch_obj.id})
                vouch_obj.is_init = True
            else:
                vouch_obj = self.env['voucher'].create({'date': money_order.date})
                money_order.write({'voucher_id': vouch_obj.id})
            if not money_order.bank_id.account_id:
                raise UserError(u'请配置%s的会计科目' % (money_order.bank_id.name))

            if money_order.is_init:
                vals.update({'init_obj': 'other_money_order-%s' % (money_order.id)})

            if money_order.type == 'other_get': # 其他收入单
                for line in money_order.line_ids:
                    if not line.category_id.account_id:
                        raise UserError(u'请配置%s的会计科目' % (line.category_id.name))

                    vals.update({'vouch_obj_id': vouch_obj.id, 'name': money_order.name, 'note': line.note or '',
                                 'credit_auxiliary_id':line.auxiliary_id.id,
                                 'amount': abs(line.amount + line.tax_amount), 'credit_account_id': line.category_id.account_id.id,
                                 'debit_account_id': money_order.bank_id.account_id.id, 'partner_credit': money_order.partner_id.id, 'partner_debit': '',
                                 'sell_tax_amount': line.tax_amount or 0,
                                 })
                    # 贷方行
                    self.env['voucher.line'].create({
                        'name': u"%s %s" % (vals.get('name'), vals.get('note')),
                        'partner_id': vals.get('partner_credit', ''),
                        'account_id': vals.get('credit_account_id'),
                        'credit': line.amount,
                        'voucher_id': vals.get('vouch_obj_id'),
                        'auxiliary_id':vals.get('credit_auxiliary_id', False),
                        'init_obj':vals.get('init_obj', False),
                    })
                    # 销项税行
                    if vals.get('sell_tax_amount'):
                        if not self.env.user.company_id.output_tax_account:
                            raise UserError(u'您还没有配置公司的销项税科目。\n请通过"配置-->高级配置-->公司"菜单来设置销项税科目!')
                        self.env['voucher.line'].create({
                            'name': u"%s %s" % (vals.get('name'), vals.get('note')),
                            'account_id': self.env.user.company_id.output_tax_account.id, 'credit': line.tax_amount or 0, 'voucher_id': vals.get('vouch_obj_id'),
                    })
                # 借方行
                self.env['voucher.line'].create({
                    'name': u"%s" % (vals.get('name')),
                    'account_id': vals.get('debit_account_id'),
                    'debit': money_order.total_amount,  # 借方和
                    'voucher_id': vals.get('vouch_obj_id'),
                    'partner_id': vals.get('partner_debit', ''),
                    'auxiliary_id':vals.get('debit_auxiliary_id', False),
                    'init_obj':vals.get('init_obj', False),
                })
            else: # 其他支出单
                for line in money_order.line_ids:
                    if not line.category_id.account_id:
                        raise UserError(u'请配置%s的会计科目' % (line.category_id.name))

                    vals.update({'vouch_obj_id': vouch_obj.id, 'name': money_order.name, 'note': line.note or '',
                                 'debit_auxiliary_id':line.auxiliary_id.id,
                                 'amount': abs(line.amount + line.tax_amount), 'credit_account_id': money_order.bank_id.account_id.id,
                                 'debit_account_id': line.category_id.account_id.id, 'partner_credit': '', 'partner_debit': money_order.partner_id.id,
                                 'buy_tax_amount': line.tax_amount or 0,
                                 })
                    # 借方行
                    self.env['voucher.line'].create({
                        'name': u"%s %s " % (vals.get('name'), vals.get('note')),
                        'account_id': vals.get('debit_account_id'),
                        'debit': line.amount,
                        'voucher_id': vals.get('vouch_obj_id'),
                        'partner_id': vals.get('partner_debit', ''),
                        'auxiliary_id':vals.get('debit_auxiliary_id', False),
                        'init_obj':vals.get('init_obj', False),
                    })
                    # 进项税行
                    if vals.get('buy_tax_amount'):
                        if not self.env.user.company_id.import_tax_account:
                            raise UserError(u'请通过"配置-->高级配置-->公司"菜单来设置进项税科目')
                        self.env['voucher.line'].create({
                            'name': u"%s %s" % (vals.get('name'), vals.get('note')),
                            'account_id': self.env.user.company_id.import_tax_account.id, 'debit': line.tax_amount or 0, 'voucher_id': vals.get('vouch_obj_id'),
                        })
                # 贷方行
                self.env['voucher.line'].create({
                    'name': u"%s" % (vals.get('name')),
                    'partner_id': vals.get('partner_credit', ''),
                    'account_id': vals.get('credit_account_id'),
                    'credit': money_order.total_amount, # 贷方和
                    'voucher_id': vals.get('vouch_obj_id'),
                    'auxiliary_id':vals.get('credit_auxiliary_id', False),
                    'init_obj':vals.get('init_obj', False),
                })
            # 删除初始非需要的凭证明细行
            if money_order.is_init:
                vouch_line_ids = self.env['voucher.line'].search([
                    ('account_id', '!=', money_order.bank_id.account_id.id),
                    ('init_obj', '=', 'other_money_order-%s' % (money_order.id))])
                for vouch_line_id in vouch_line_ids:
                    vouch_line_id.unlink()
            else:
                vouch_obj.voucher_done()
        return res


class money_transfer_order(models.Model):
    _inherit = 'money.transfer.order'
    voucher_id = fields.Many2one('voucher', u'对应凭证', readonly=True, ondelete='restrict',
                                 help=u'资金转账单审核时生成的对应凭证', copy=False)

    '''外币转外币暂时不做，只处理外币转本位币'''
    @api.multi
    def money_transfer_done(self):
        """
        审核资金转账单时，生成凭证
        :return: 
        """
        self.ensure_one()
        res = super(money_transfer_order, self).money_transfer_done()
        vouch_obj = self.env['voucher'].create({'date': self.date})
        vals = {}
        self.write({'voucher_id': vouch_obj.id})
        for line in self.line_ids:
            out_currency_id = line.out_bank_id.account_id.currency_id.id or self.env.user.company_id.currency_id.id
            in_currency_id = line.in_bank_id.account_id.currency_id.id or self.env.user.company_id.currency_id.id
            company_currency_id = self.env.user.company_id.currency_id.id
            if (out_currency_id != company_currency_id or in_currency_id != company_currency_id) and not line.currency_amount :
                raise UserError(u'错误' u'请请输入外币金额。')
            if line.currency_amount and out_currency_id != company_currency_id:
                '''结汇'''
                '''借方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s结汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.in_bank_id.account_id.id, 'debit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': '',
                })
                '''贷方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s结汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.out_bank_id.account_id.id, 'credit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': out_currency_id,
                    'currency_amount': line.currency_amount, 'rate_silent': line.amount / line.currency_amount
                })
            elif line.currency_amount and in_currency_id != company_currency_id:
                '''买汇'''
                '''借方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s买汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.in_bank_id.account_id.id, 'debit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': in_currency_id,
                    'currency_amount': line.currency_amount, 'rate_silent': line.amount / line.currency_amount
                })
                '''贷方行'''
                self.env['voucher.line'].create({
                    'name': u"%s %s买汇至%s %s" % (self.name, line.out_bank_id.name, line.in_bank_id.name, self.note),
                    'account_id': line.out_bank_id.account_id.id, 'credit': line.amount,
                    'voucher_id': vouch_obj.id, 'partner_id': '', 'currency_id': '',
                })
            else:
                '''人民币间'''
                vals.update({'vouch_obj_id': vouch_obj.id, 'name': self.name, 'string': self.note or '',
                         'amount': abs(line.amount), 'credit_account_id': line.out_bank_id.account_id.id,
                         'debit_account_id': line.in_bank_id.account_id.id,
                         })
                self.env['money.invoice'].create_voucher_line(vals)

        # if self.discount_amount > 0:
        #     self.env['voucher.line'].create({
        #         'name': u"其他转账单%s" % (self.name),
        #         'account_id': self.discount_account_id.id,
        #         'credit': self.discount_amount,
        #         'voucher_id': vouch_obj.id,
        #         'partner_id': '',
        #     })

        vouch_obj.voucher_done()
        return res

    @api.multi
    def money_transfer_draft(self):
        self.ensure_one()
        res = super(money_transfer_order, self).money_transfer_draft()
        voucher, self.voucher_id = self.voucher_id, False
        if voucher.state == 'done':
            voucher.voucher_draft()
        voucher.unlink()
        return res
