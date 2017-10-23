# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError

change = [('time', u'计时'),
          ('piece', u'计件'),
          ('efficiency', u'计效')]


class CREATEWAGESLINEWIZARD(models.TransientModel):
    _name = 'create.wages.line.wizard'
    _description = 'input staff wages'

    wages_change = fields.Selection(change, u'记工类型')

    @api.one
    def input_change_wages(self):
        if not self.env.context.get('active_id'):
            return
        date = fields.Date.context_today(self)
        wages = self.env['staff.wages'].browse(
            self.env.context.get('active_id'))
        staff_ids = self.env['staff'].search(['&',
                                              ('active', '=', True),
                                              ('contract_ids', '!=', False)])
        for id in staff_ids:
            for line in id.contract_ids:
                if date < line.over_date and (self.wages_change == line.wages_change or not self.wages_change):
                    self.env['wages.line'].create({'name': id.id,
                                                   'order_id': wages.id,
                                                   'basic_wage': line.basic_wage,
                                                   'endowment': line.endowment,
                                                   'health': line.health,
                                                   'unemployment': line.unemployment,
                                                   'housing_fund': line.housing_fund})
                    continue
