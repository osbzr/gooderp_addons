# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import fields, models, api


class PartnerStatementsReportWizard(models.TransientModel):
    _name = "partner.statements.report.wizard"
    _description = u"业务伙伴对账单向导"

    @api.model
    def _get_company_start_date(self):
        return self._get_company_start_date_impl()

    @api.model
    def _get_company_start_date_impl(self):
        ''' 获取当前登录用户公司的启用日期 '''
        return self.env.user.company_id.start_date

    partner_id = fields.Many2one('partner', string=u'业务伙伴', required=True,
                                 help=u'查看某一个业务伙伴的对账单报表')
    from_date = fields.Date(string=u'开始日期', required=True, default=_get_company_start_date,
                            help=u'查看本次报表的开始日期')  # 默认公司启用日期
    to_date = fields.Date(string=u'结束日期', required=True,
                          default=lambda self: fields.Date.context_today(self),
                          help=u'查看本次报表的结束日期')  # 默认当前日期
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    is_doc = fields.Boolean(u'打印word格式')

    @api.multi
    def partner_statements_without_goods(self):
        """
        业务伙伴对账单: 不带商品明细
        :return: action
        """
        for s in self:
            if s.from_date > s.to_date:
                raise UserError(u'结束日期不能小于开始日期！\n开始日期:%s 结束日期:%s ' %
                                (s.from_date, s.to_date))

            if self.env.context.get('default_customer'):  # 客户
                view = self.env.get('sell.order') != None \
                    and self.env.ref('sell.customer_statements_report_tree') \
                    or self.env.ref('money.customer_statements_report_simple_tree')
                name = u'客户对账单:' + s.partner_id.name
                res_model = 'customer.statements.report'
            else:  # 供应商
                view = self.env.get('buy.order') != None \
                    and self.env.ref('buy.supplier_statements_report_tree') \
                    or self.env.ref('money.supplier_statements_report_simple_tree')
                name = u'供应商对账单:' + s.partner_id.name
                res_model = 'supplier.statements.report'

            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': res_model,
                'view_id': False,
                'views': [(view.id, 'tree')],
                'limit': 65535,
                'type': 'ir.actions.act_window',
                'domain': [('partner_id', '=', s.partner_id.id), ('date', '>=', s.from_date), ('date', '<=', s.to_date)]
            }

    def _create_statements_report_with_goods(self, partner_id, name, date, done_date, order_amount,
                                             benefit_amount, fee, amount, pay_amount, discount_money,
                                             balance_amount, note, move_id, ptype):
        """
        生成无商品明细的对账单记录
        """
        if ptype == 'customer':
            model = self.env['customer.statements.report.with.goods']
        else:
            model = self.env['supplier.statements.report.with.goods']
        record_id = model.create({
            'partner_id': partner_id,
            'name': name,
            'date': date,
            'done_date': done_date,
            'order_amount': order_amount,
            'benefit_amount': benefit_amount,
            'fee': fee,
            'amount': amount,
            'pay_amount': pay_amount,
            'discount_money': discount_money,
            'balance_amount': balance_amount,
            'note': note,
            'move_id': move_id}).id

        return record_id

    def _create_statements_report_with_goods_line(self, goods_code, goods_name, attribute_id, uom_id,
                                                  quantity, price, discount_amount, without_tax_amount,
                                                  tax_amount, order_amount, balance_amount, ptype):
        """
        生成带商品明细的对账单记录
        """
        if ptype == 'customer':
            model = self.env['customer.statements.report.with.goods']
        else:
            model = self.env['supplier.statements.report.with.goods']

        record_id = model.create({
            'goods_code': goods_code,
            'goods_name': goods_name,
            'attribute_id': attribute_id,
            'uom_id': uom_id,
            'quantity': quantity,
            'price': price,
            'discount_amount': discount_amount,
            'without_tax_amount': without_tax_amount,
            'tax_amount': tax_amount,
            'order_amount': order_amount,
            'balance_amount': balance_amount}).id

        return record_id

    @api.multi
    def partner_statements_with_goods(self):
        """
        业务伙伴对账单: 带商品明细
        :return: action
        """
        for s in self:
            res_ids = []
            if s.from_date > s.to_date:
                raise UserError(u'结束日期不能小于开始日期。\n开始日期:%s 结束日期:%s ' %
                                (s.from_date, s.to_date))

            if self.env.context.get('default_customer'):  # 客户
                reports = self.env['customer.statements.report'].search([('partner_id', '=', s.partner_id.id),
                                                                         ('date', '>=',
                                                                          s.from_date),
                                                                         ('date', '<=', s.to_date)])
                for report in reports:
                    # 生成无商品明细的对账单记录
                    record_id = self._create_statements_report_with_goods(report.partner_id.id,
                                                                          report.name,
                                                                          report.date,
                                                                          report.done_date,
                                                                          report.sale_amount,
                                                                          report.benefit_amount,
                                                                          report.fee,
                                                                          report.amount,
                                                                          report.pay_amount,
                                                                          report.discount_money,
                                                                          report.balance_amount,
                                                                          report.note,
                                                                          report.move_id.id,
                                                                          'customer')
                    res_ids.append(record_id)

                    # 生成带商品明细的对账单记录
                    if report.move_id:
                        # report.amount<0时为销售退货单，否则为销售发货单
                        line_ids = (report.amount < 0 and report.move_id.line_in_ids
                                    or report.move_id.line_out_ids)
                        for line in line_ids:
                            record_id = self._create_statements_report_with_goods_line(line.goods_id.code,
                                                                                       line.goods_id.name,
                                                                                       line.attribute_id.id,
                                                                                       line.uom_id.id,
                                                                                       line.goods_qty,
                                                                                       line.price,
                                                                                       line.discount_amount,
                                                                                       line.amount,
                                                                                       line.tax_amount,
                                                                                       line.subtotal,
                                                                                       report.balance_amount,
                                                                                       'customer')
                            res_ids.append(record_id)
                view = self.env.ref(
                    'sell.customer_statements_report_with_goods_tree')

                return {
                    'name': u'客户对账单:' + s.partner_id.name,
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'customer.statements.report.with.goods',
                    'view_id': False,
                    'views': [(view.id, 'tree')],
                    'limit': 65535,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', res_ids)],
                    'context': {'is_customer': True, 'is_supplier': False},
                }
            else:  # 供应商
                reports = self.env['supplier.statements.report'].search([('partner_id', '=', s.partner_id.id),
                                                                         ('date', '>=',
                                                                          s.from_date),
                                                                         ('date', '<=', s.to_date)])
                for report in reports:
                    # 生成带商品明细的对账单记录
                    record_id = self._create_statements_report_with_goods(report.partner_id.id,
                                                                          report.name,
                                                                          report.date,
                                                                          report.done_date,
                                                                          report.purchase_amount,
                                                                          report.benefit_amount,
                                                                          0,
                                                                          report.amount,
                                                                          report.pay_amount,
                                                                          report.discount_money,
                                                                          report.balance_amount,
                                                                          report.note,
                                                                          report.move_id.id,
                                                                          'supplier')
                    res_ids.append(record_id)

                    # 生成带商品明细的对账单记录
                    if report.move_id:
                        # report.amount<0时为采购退货单，否则为采购入库单
                        line_ids = (report.amount < 0 and report.move_id.line_out_ids
                                    or report.move_id.line_in_ids)
                        for line in line_ids:
                            record_id = self._create_statements_report_with_goods_line(line.goods_id.code,
                                                                                       line.goods_id.name,
                                                                                       line.attribute_id.id,
                                                                                       line.uom_id.id,
                                                                                       line.goods_qty,
                                                                                       line.price,
                                                                                       line.discount_amount,
                                                                                       line.amount,
                                                                                       line.tax_amount,
                                                                                       line.subtotal,
                                                                                       report.balance_amount,
                                                                                       'supplier')
                            res_ids.append(record_id)

                view = self.env.ref(
                    'buy.supplier_statements_report_with_goods_tree')

                return {
                    'name': u'供应商对账单:' + s.partner_id.name,
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'supplier.statements.report.with.goods',
                    'view_id': False,
                    'views': [(view.id, 'tree')],
                    'limit': 65535,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', res_ids)],
                    'context': {'is_customer': False, 'is_supplier': True},
                }

    @api.onchange('from_date')
    def onchange_from_date(self):
        """
        客户对账单向导上过滤出是客户的业务伙伴，供应商上过滤出是供应商的业务伙伴
        :return: domain
        """
        if self.env.context.get('default_customer'):
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}
