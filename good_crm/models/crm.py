# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class Opportunity(models.Model):
    _name = 'opportunity'
    _inherits = {'task': 'task_id'}
    _inherit = ['mail.thread']
    _order = 'planned_revenue desc, priority desc, id'
    _description = u'商机'

    @api.model
    def _select_objects(self):
        records = self.env['business.data.table'].search([])
        models = self.env['ir.model'].search(
            [('model', 'in', [record.name for record in records])])
        return [(model.model, model.name) for model in models]

    @api.one
    @api.depends('line_ids.price', 'line_ids.quantity')
    def _compute_total_amount(self):
        """
        计算报价总额
        :return:
        """
        self.total_amount = sum(
            line.price * line.quantity for line in self.line_ids)

    task_id = fields.Many2one('task',
                              u'任务',
                              ondelete='cascade',
                              required=True)
    planned_revenue = fields.Float(u'预期收益',
                                   track_visibility='always')
    ref = fields.Reference(string=u'相关记录',
                           selection='_select_objects')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    partner_id = fields.Many2one(
        'partner',
        u'客户',
        ondelete='restrict',
        help=u'待签约合同的客户',
    )
    date = fields.Date(u'预计采购时间')
    line_ids = fields.One2many(
        'goods.quotation',
        'opportunity_id',
        string=u'商品报价',
        copy=True,
    )
    total_amount = fields.Float(
        u'报价总额',
        track_visibility='always',
        compute='_compute_total_amount',
    )
    success_reason_id = fields.Many2one(
        'core.value',
        u'成功原因',
        ondelete='restrict',
        domain=[('type', '=', 'success_reason')],
        context={'type': 'success_reason'},
        help=u'成功原因分析',
    )

    @api.multi
    def assign_to_me(self):
        ''' 继承任务 指派给自己，将商机指派给自己，并修改状态 '''
        self.task_id.assign_to_me()


class GoodsQuotation(models.Model):
    _name = 'goods.quotation'
    _description = u'商品报价'

    opportunity_id = fields.Many2one('opportunity',
                                     u'商机',
                                     index=True,
                                     required=True,
                                     ondelete='cascade',
                                     help=u'关联的商机')
    goods_id = fields.Many2one('goods',
                               u'商品',
                               ondelete='restrict',
                               help=u'商品')
    quantity = fields.Float(u'数量',
                            default=1,
                            digits=dp.get_precision('Quantity'),
                            help=u'数量')
    price = fields.Float(u'单价',
                         required=True,
                         digits=dp.get_precision('Price'),
                         help=u'商品报价')
    note = fields.Char(u'描述',
                       help=u'商品描述')
