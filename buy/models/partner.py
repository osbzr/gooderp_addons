# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'partner'

    @api.multi
    def action_view_buy_history(self):
        '''
        This function returns an action that display buy history of given sells order ids.
        Date range [180 days ago, now]
        '''
        self.ensure_one()
        date_end = datetime.today()
        date_start = datetime.strptime(
            self.env.user.company_id.start_date, '%Y-%m-%d')

        if (date_end - date_start).days > 180:
            date_start = date_end - datetime.timedelta(days=180)

        buy_order_track_wizard_obj = self.env['buy.order.track.wizard'].create({'date_start': date_start,
                                                                                'date_end': date_end,
                                                                                'partner_id': self.id})

        return buy_order_track_wizard_obj.button_ok()
