# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm


class buy_payment_wizard(models.TransientModel):
    _name = 'buy.payment.wizard'
    _description = u'采购付款一览表向导'

    @api.model
    def _default_date_start(self):
        return self.env.user.company_id.start_date

    @api.model
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(u'开始日期', default=_default_date_start)
    date_end = fields.Date(u'结束日期', default=_default_date_end)
    s_category_id = fields.Many2one('core.category', u'供应商类别')
    partner_id = fields.Many2one('partner', u'供应商')
    order_id = fields.Many2one('buy.receipt', u'采购单号')

    '''@api.multi
    def button_ok(self):
        res = []
        if self.date_end < self.date_start:
            raise except_orm(u'错误', u'开始日期不能大于结束日期！')

        cond = [('date', '>=', self.date_start),
                ('date', '<=', self.date_end),
                ('state', '=', 'done')]
        if self.s_category_id:
            cond.append(('partner_id.s_category_id', '=', self.s_category_id.id))
        if self.partner_id:
            cond.append(('partner_id', '=', self.partner_id.id))
        if self.order_id:
            cond.append(('name', '=', self.order_id.id))

        for receipt in self.env['buy.receipt'].search(cond, order='partner_id'):
            if not receipt.is_return:
                type = u'普通采购'
            elif receipt.is_return:
                type = u'采购退回'
            # FIXME: 付款
            detail = self.env['buy.payment'].create({
                    's_category': receipt.partner_id.s_category_id.id,
                    'partner_id': receipt.partner_id.id,
                    'type': type,
                    'date': receipt.date,
                    'order_name': receipt.name,
                    'purchase_amount': receipt.discount_amount + receipt.amount,
                    'discount_amount': receipt.discount_amount,
                    'amount': receipt.amount,
                    'payment': receipt.payment,
                    'balance': receipt.debt,
                    'note': receipt.note,
                })
            res.append(detail.id)
            for source in self.env['money.order'].source_ids:
                if source.name.id == receipt.id:
                    detail = self.env['buy.payment'].create({
                        'type': u'付款',
                        'date': receipt.date,
                        'order_name': receipt.name,
                        'payment': receipt.payment,
                        'note': receipt.note,
                })
            res.append(detail.id)
        view = self.env.ref('buy.buy_payment_tree')
        return {
            'name': u'采购付款一览表',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'views': [(view.id, 'tree')],
            'res_model': 'buy.payment',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)],
            'limit': 300,
        }'''
