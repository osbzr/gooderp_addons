# -*- coding: utf-8 -*-

from datetime import datetime,timedelta
from odoo import api, fields, models


class Partner(models.Model):
    '''
    业务伙伴可能是客户： c_category_id 非空

    '''
    _inherit = 'partner'

    @api.multi
    def action_view_sell_history(self):
        '''
        This function returns an action that display sell history of given sells order ids.
        Date range [365 days ago, now]
        '''

        self.ensure_one()
        date_end = datetime.today()
        date_start = datetime.strptime(
            self.env.user.company_id.start_date, '%Y-%m-%d')

        if (date_end - date_start).days > 365:
            date_start = date_end - timedelta(days=365)

        sell_order_track_wizard_obj = self.env['sell.order.track.wizard'].create({'date_start': date_start,
                                                                                  'date_end': date_end,
                                                                                  'partner_id': self.id})

        return sell_order_track_wizard_obj.button_ok()
