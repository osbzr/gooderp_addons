# -*- coding: utf-8 -*-
from openerp.exceptions import except_orm
from openerp import fields, models, api

class partner_statements_report_wizard(models.TransientModel):
    _name = "partner.statements.report.wizard"
    _description = u"业务伙伴对账单向导"

    @api.model
    def _get_company_start_date(self):
        return self.env.user.company_id.start_date

    partner_id = fields.Many2one('partner', string=u'业务伙伴', required=True)
    from_date = fields.Date(string=u'开始日期', required=True, default=_get_company_start_date)  # 默认公司启用日期
    to_date = fields.Date(string=u'结束日期', required=True, default=lambda self: fields.Date.context_today(self))  # 默认当前日期

    @api.multi
    def partner_statements_without_goods(self):
        # 业务伙伴对账单: 不带商品明细
        if self.from_date > self.to_date:
            raise except_orm(u'错误！', u'结束日期不能小于开始日期！')

        if self._context.get('default_customer'):  # 客户
            view = self.env.ref('sell.customer_statements_report_tree')
            name = u'客户对账单:' + self.partner_id.name
            res_model = 'customer.statements.report'
        else:  # 供应商
            view = self.env.ref('buy.supplier_statements_report_tree')
            name = u'供应商对账单:' + self.partner_id.name
            res_model = 'supplier.statements.report'

        return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': res_model,
                'view_id': False,
                'views': [(view.id, 'tree')],
                'type': 'ir.actions.act_window',
                'domain':[('partner_id', '=', self.partner_id.id), ('date', '>=', self.from_date), ('date', '<=', self.to_date)]
                }

    @api.multi
    def partner_statements_with_goods(self):
        # 业务伙伴对账单: 带商品明细
        res_ids = []
        if self.from_date > self.to_date:
            raise except_orm(u'错误！', u'结束日期不能小于开始日期！')

        if self._context.get('default_customer'):  # 客户
            reports = self.env['customer.statements.report'].search([('partner_id', '=', self.partner_id.id),
                                                                    ('date', '>=', self.from_date),
                                                                    ('date', '<=', self.to_date)])
            for report in reports:
                # 生成不带商品明细的对账单记录
                res_ids.append(self.env['customer.statements.report.with.goods'].create({
                        'partner_id': report.partner_id.id,
                        'name': report.name,
                        'date': report.date,
                        'order_amount': report.sale_amount,
                        'benefit_amount': report.benefit_amount,
                        'fee': report.fee,
                        'amount': report.amount,
                        'pay_amount': report.pay_amount,
                        'balance_amount': report.balance_amount,
                        'note': report.note,
                        'move_id': report.move_id.id}).id)

                # 生成带商品明细的对账单记录
                if report.move_id:
                    if report.amount < 0: # 销售退货单
                        for line in report.move_id.line_in_ids:
                            res_ids.append(self.env['customer.statements.report.with.goods'].create({
                                    'goods_code': line.goods_id.code,
                                    'goods_name': line.goods_id.name,
                                    'attribute_id': line.attribute_id.id,
                                    'uom_id': line.uom_id.id,
                                    'quantity': line.goods_qty,
                                    'price': line.price,
                                    'discount_amount': line.discount_amount,
                                    'without_tax_amount': line.amount,
                                    'tax_amount': line.tax_amount,
                                    'order_amount': line.subtotal,
                                    'balance_amount': report.balance_amount
                                    }).id)
                    else:
                        for line in report.move_id.line_out_ids: # 销售发货单
                            res_ids.append(self.env['customer.statements.report.with.goods'].create({
                                    'goods_code': line.goods_id.code,
                                    'goods_name': line.goods_id.name,
                                    'attribute_id': line.attribute_id.id,
                                    'uom_id': line.uom_id.id,
                                    'quantity': line.goods_qty,
                                    'price': line.price,
                                    'discount_amount': line.discount_amount,
                                    'without_tax_amount': line.amount,
                                    'tax_amount': line.tax_amount,
                                    'order_amount': line.subtotal,
                                    'balance_amount': report.balance_amount
                                    }).id)

            view = self.env.ref('sell.customer_statements_report_with_goods_tree')

            return {
                    'name': u'客户对账单:' + self.partner_id.name,
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'customer.statements.report.with.goods',
                    'view_id': False,
                    'views': [(view.id, 'tree')],
                    'type': 'ir.actions.act_window',
                    'domain':[('id', 'in', res_ids)],
                    'context': {'is_customer': True, 'is_supplier': False},
                    }
        else:  # 供应商
            reports = self.env['supplier.statements.report'].search([('partner_id', '=', self.partner_id.id),
                                                                    ('date', '>=', self.from_date),
                                                                    ('date', '<=', self.to_date)])
            for report in reports:
                # 生成不带商品明细的对账单记录
                res_ids.append(self.env['supplier.statements.report.with.goods'].create({
                        'partner_id': report.partner_id.id,
                        'name': report.name,
                        'date': report.date,
                        'order_amount': report.purchase_amount,
                        'benefit_amount': report.benefit_amount,
                        'amount': report.amount,
                        'pay_amount': report.pay_amount,
                        'balance_amount': report.balance_amount,
                        'note': report.note,
                        'move_id': report.move_id.id}).id)

                # 生成带商品明细的对账单记录
                if report.move_id:
                    if report.amount < 0: # 采购退货单
                        for line in report.move_id.line_out_ids:
                            res_ids.append(self.env['supplier.statements.report.with.goods'].create({
                                    'goods_code': line.goods_id.code,
                                    'goods_name': line.goods_id.name,
                                    'attribute_id': line.attribute_id.id,
                                    'uom_id': line.uom_id.id,
                                    'quantity': line.goods_qty,
                                    'price': line.price,
                                    'discount_amount': line.discount_amount,
                                    'without_tax_amount': line.amount,
                                    'tax_amount': line.tax_amount,
                                    'order_amount': line.subtotal,
                                    'balance_amount': report.balance_amount
                                    }).id)
                    else: # 采购入库单
                        for line in report.move_id.line_in_ids:
                            res_ids.append(self.env['supplier.statements.report.with.goods'].create({
                                    'goods_code': line.goods_id.code,
                                    'goods_name': line.goods_id.name,
                                    'attribute_id': line.attribute_id.id,
                                    'uom_id': line.uom_id.id,
                                    'quantity': line.goods_qty,
                                    'price': line.price,
                                    'discount_amount': line.discount_amount,
                                    'without_tax_amount': line.amount,
                                    'tax_amount': line.tax_amount,
                                    'order_amount': line.subtotal,
                                    'balance_amount': report.balance_amount
                                    }).id)

            view = self.env.ref('buy.supplier_statements_report_with_goods_tree')

            return {
                    'name': u'供应商对账单:' + self.partner_id.name,
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'supplier.statements.report.with.goods',
                    'view_id': False,
                    'views': [(view.id, 'tree')],
                    'type': 'ir.actions.act_window',
                    'domain':[('id', 'in', res_ids)],
                    'context': {'is_customer': False, 'is_supplier': True},
                    }

    @api.onchange('from_date')
    def onchange_from_date(self):
        if self._context.get('default_customer'):
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}
