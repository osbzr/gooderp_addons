# -*- coding: utf-8 -*-
##############################################################################
#
#    Auto reset sequence by year,month,day
#    Copyright 2013 wangbuke <wangbuke@gmail.com>
#    Copyright 2017 开阖软件 <www.osbzr.com>   port to GoodERP v11
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

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pytz
from datetime import datetime


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    auto_reset = fields.Boolean('Auto Reset')
    reset_period = fields.Selection(
        [('year', 'Every Year'), ('month', 'Every Month'), ('day', 'Every Day'),
         ('h24', 'Every Hour'), ('min', 'Every Minute'), ('sec', 'Every Second')],
        'Reset Period', required=True, default='month')
    reset_time = fields.Char('Last reset time', size=64,
                             help="Last time the sequence was reset")
    reset_init_number = fields.Integer(
        'Reset Number', required=True, default=1, help="Reset number of this sequence")

    def get_next_char(self, number_next):
        def _interpolation_dict():
            now = range_date = effective_date = datetime.now(
                pytz.timezone(self._context.get('tz') or 'UTC'))
            if self._context.get('ir_sequence_date'):
                effective_date = datetime.strptime(
                    self._context.get('ir_sequence_date'), '%Y-%m-%d')
            if self._context.get('ir_sequence_date_range'):
                range_date = datetime.strptime(self._context.get(
                    'ir_sequence_date_range'), '%Y-%m-%d')
            sequences = {'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                         'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'}
            res = {}
            for key, format in sequences.iteritems():
                res[key] = effective_date.strftime(format)
                res['range_' + key] = range_date.strftime(format)
                res['current_' + key] = now.strftime(format)
            return res

        d = _interpolation_dict()
        current_time = d.get(self['reset_period'])
        number_next_actual = False
        if self['auto_reset'] and current_time != self['reset_time']:
            self.env.cr.execute(
                "UPDATE ir_sequence SET reset_time=%s WHERE id=%s ", (current_time, self['id']))
            self.env.cr.commit()
            number_next = (self['reset_init_number'],)
            number_next_actual = self['reset_init_number'] + \
                self['number_increment']
        return_vals = super(IrSequence, self).get_next_char(number_next)
        if number_next_actual:
            self.sudo().number_next_actual = number_next_actual
            self.sudo().number_next = number_next_actual
        return return_vals
