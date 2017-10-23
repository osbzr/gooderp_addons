# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class BusinessDataTable(models.Model):
    _name = 'business.data.table'
    _description = u'业务数据表'

    model = fields.Many2one('ir.model', u'需要清理的表')
    name = fields.Char(u'业务数据表名', required=True)
    clean_business_id = fields.Many2one(
        'clean.business.data', string=u'清理数据对象')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.onchange('model')
    def onchange_model(self):
        self.name = self.model and self.model.model


class CleanBusinessData(models.Model):
    _name = 'clean.business.data'
    _description = u'清理记录'

    @api.model
    def _get_business_table_name(self):
        return self._get_business_table_name_impl()

    @api.model
    def _get_business_table_name_impl(self):
        '''
                         默认取business.data.table 里的所有业务数据表清理
        '''
        return self.env['business.data.table'].search([])

    need_clean_table = fields.One2many('business.data.table', 'clean_business_id',
                                       default=_get_business_table_name,
                                       string='要清理的业务数据表')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def remove_data(self):
        try:
            for line in self.need_clean_table:
                obj_name = line.name
                obj = self.env[obj_name]
                if obj._table_exist:
                    sql = "TRUNCATE TABLE %s CASCADE " % obj._table
                    self.env.cr.execute(sql)
        except Exception, e:
            raise UserError(e)
        return True
