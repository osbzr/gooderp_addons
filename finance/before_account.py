# -*- coding: utf-8 -*-

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime

# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
    }

class before_account(models.Model):
    '''会计凭证初始化'''
    _name = 'before.account'

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        current_date = self.date
        if not self.period_id:
            if current_date:
                self.env['finance.period'].create({'year': current_date[0:4],
                                'month': str(int(current_date[5:7])), })
        self.period_id = self.env['finance.period'].get_period(self.date)
    name = fields.Char(u'名称', required=True)
    date = fields.Date(u'记帐日期', required=True)
    period_id = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    line_ids = fields.One2many('before.line', 'order_id', u'初始明细行',
                               states=READONLY_STATES, copy=True)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核')], u'状态', default='draft')

    @api.one
    def asset_done(self):
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if self.period_id.is_closed is True:
            raise except_orm(u'错误', u'该会计期间已结账！不能审核')
        self.state = 'done'

    @api.one
    def before_asset(self):
        '''删除以前引入的固定资产内容'''
        for line in self.line_ids :
            if line.cate == 'asset':
                line.unlink()

        '''引入固定资产初始化单据'''
        res = {}
        for asset in self.env['asset'].search([('other_system', '=', True)]):
            cost = asset.cost
            depreciation_value2 = asset.depreciation_value2
            '''固定资产'''
            if asset.account_asset.id not in res:
                res[asset.account_asset.id] = {'credit':0,'debit': 0,'cate':'asset'}

            val = res[asset.account_asset.id]
            val.update({'debit':val.get('debit') + cost,
                        'account_id': asset.account_asset.id,
                        'order_id': self.id,
                        })
            '''累计折旧'''
            if asset.account_depreciation2.id not in res:
                res[asset.account_depreciation2.id] = {'credit':0,'debit': 0,'cate':'asset'}

            val = res[asset.account_depreciation2.id]
            val.update({'credit':val.get('credit') + depreciation_value2,
                        'account_id': asset.account_depreciation2.id,
                        'order_id': self.id,
                        })

        for account_id,val in res.iteritems():
            self.env['before.line'].create(dict(val,account_id = account_id))
            print account_id,val

    @api.one
    def before_partner(self):
        '''删除以前引入的固定资产内容'''
        for line in self.line_ids :
            if line.cate == 'partner':
                line.unlink()


        for partner in self.env['partner'].search([('name', '!=', 'false')]):
            self.env['before.line'].create({
                'account_id':partner.c_category_id.account_id.id or partner.s_category_id.account_id.id,
                'partner_id':partner.id,
                'order_id':self.id,
                'debit':partner.receivable_init or 0,
                'credit':partner.payable_init or 0,
                'cate': 'partner',
            })

    @api.one
    def before_capital(self):

        '''删除以前引入的资金内容'''
        for line in self.line_ids :
            if line.cate == 'capital':
                line.unlink()

        for bank in self.env['bank.account'].search([('name', '!=', 'false')]):
            self.env['before.line'].create({
                'account_id':bank.account_id.id ,
                'order_id':self.id,
                'debit':bank.before or 0,
                'credit':0,
                'cate': 'capital',
            })

            bank.balance += bank.before

    @api.one
    def before_warehouse(self):
        '''删除以前引入的仓库内容'''
        for line in self.line_ids :
            if line.cate == 'warehouse':
                line.unlink()
        res = {}

        for wh_id in self.env['wh.in'].search([('before', '=', True)]):
            account_id = wh_id.move_id.warehouse_dest_id.account_id.id
            if not account_id :
                raise except_orm(u'错误', u'请为仓库配置科目')

            if account_id not in res:
                res[account_id] = {'debit': 0}

            val = res[account_id]
            val.update({
                'account_id':account_id,
                'order_id':self.id,
                'debit': val.get('debit') + wh_id.amount_total,
                'credit': 0,
                'cate': 'warehouse',
                            })

        for account_id,val in res.iteritems():
            self.env['before.line'].create(dict(val,account_id = account_id))
            print account_id,val

    @api.one
    def asset_done(self):
        if self.state == 'done':
            raise except_orm(u'错误', u'请不要重复审核！')
        if self.period_id.is_closed is True:
            raise except_orm(u'错误', u'该会计期间已结账！不能审核')
        self.state = 'done'
        '''如果借贷相等则结束初使化，生成凭证'''
        sumdebit = sum(line.debit for line in self.line_ids)
        sumcredit = sum(line.credit for line in self.line_ids)

        if sumcredit != sumdebit :
            raise except_orm(u'错误', u'借贷不相等')
        else:
            vouch_obj = self.env['voucher'].create({'date': self.date})
            self.write({'voucher_id': vouch_obj.id})
            for line in self.line_ids:
                if not (line.debit == 0 or line.credit==0):
                    raise except_orm(u'错误', u'借贷不能同时有值')
                self.env['voucher.line'].create({'voucher_id': vouch_obj.id, 'name': u'初始化凭证',
                     'debit': line.debit, 'account_id': line.account_id.id,'credit': line.credit,
                     'partner_id': line.partner_id.id or '', 'auxiliary_id': False
                     })

    @api.one
    def asset_draft(self):
        if self.state == 'draft':
            raise except_orm(u'错误', u'请不要重复反审核！')
        if self.period_id.is_closed is True:
            raise except_orm(u'错误', u'该会计期间已结账！不能反审核')
        self.state = 'draft'


class before_line(models.Model):
    '''财务初始化明细行'''
    _name = 'before.line'

    account_id = fields.Many2one('finance.account', u'会计科目', required=True)
    partner_id = fields.Many2one('partner', u'往来单位', ondelete='restrict')
    order_id = fields.Many2one('before.account', u'初始化编号', select=True,
                               required=True, ondelete='cascade')
    debit = fields.Float(u'借方初始金额', digits_compute=dp.get_precision(u'借方金额'), required=True)
    credit = fields.Float(u'贷方初始金额', digits_compute=dp.get_precision(u'贷方金额'), required=True)
    cate = fields.Char(u'标记')

class warehouse(models.Model):
    _inherit = 'warehouse'
    account_id = fields.Many2one('finance.account', u'记帐科目')

class bank_account(models.Model):
    _inherit = 'bank.account'
    before = fields.Float(u'初始金额',digits_compute=dp.get_precision('Amount'))

