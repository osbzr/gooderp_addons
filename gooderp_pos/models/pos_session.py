# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError

class PosSession(models.Model):
    _name = 'pos.session'
    _order = 'id desc'
    _description = u'工作记录'

    POS_SESSION_STATE = [
        ('opening_control', '新的工作记录'),  # method action_pos_session_open
        ('opened', '销售过程'),               # method action_pos_session_closing_control
        ('closed', '关闭 & 过账'),
    ]

    config_id = fields.Many2one('pos.config', string='POS', required=True, index=True)
    name = fields.Char(string='工作记录名', required=True, readonly=True, default='/')
    user_id = fields.Many2one(
        'res.users', string='负责人',
        required=True,
        index=True,
        readonly=True,
        states={'opening_control': [('readonly', False)]},
        default=lambda self: self.env.uid)
    #TODO:currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency")
    start_at = fields.Datetime(string='打开日期', readonly=True)
    stop_at = fields.Datetime(string='关闭日期', readonly=True, copy=False)

    state = fields.Selection(
        POS_SESSION_STATE, string='Status',
        required=True, readonly=True,
        index=True, copy=False, default='opening_control')
    sequence_number = fields.Integer(string='Order Sequence Number', default=1)
    login_number = fields.Integer(string='Login Sequence Number', default=0)
    cash_control = fields.Boolean( string='Has Cash Control')
    payment_line_ids = fields.One2many('payment.line', 'session_id', string='支付详情')

    _sql_constraints = [('uniq_name', 'unique(name)', _("The name of this POS Session must be unique !"))]

    @api.multi
    def action_pos_session_open(self):
        # second browse because we need to refetch the data from the DB for cash_register_id
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            values = {}
            if not session.start_at:
                values['start_at'] = fields.Datetime.now()
            values['state'] = 'opened'
            session.write(values)
            # session.statement_ids.button_open()
        return True

    @api.constrains('config_id')
    def _check_pos_config(self):
        if self.search_count([
                ('state', '!=', 'closed'),
                ('config_id', '=', self.config_id.id),
                ('name', 'not like', 'RESCUE FOR'),
            ]) > 1:
            raise ValidationError(_("You cannot create two active sessions related to the same point of sale!"))

    @api.model
    def create(self, values):
        if values.get('session_id'):
            session = self.env['pos.session'].browse(values['session_id'])
            values['name'] = session.config_id.sequence_id._next()
            values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
        else:
            # fallback on any pos.order sequence
            values['name'] = self.env['ir.sequence'].next_by_code('pos.order')
        res = super(PosSession, self).create(values)
        return res

    @api.multi
    def unlink(self):
        return super(PosSession, self).unlink()

    @api.multi
    def login(self):
        self.ensure_one()
        self.write({
            'login_number': self.login_number + 1,
        })

    @api.multi
    def action_pos_session_open(self):
        # second browse because we need to refetch the data from the DB for cash_register_id
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            values = {}
            if not session.start_at:
                values['start_at'] = fields.Datetime.now()
            values['state'] = 'opened'
            session.write(values)
            #session.statement_ids.button_open()
        return True

    @api.multi
    def open_frontend_cb(self):
        if not self.ids:
            return {}
        for session in self.filtered(lambda s: s.user_id.id != self.env.uid):
            raise UserError(_("You cannot use the session of another users. This session is owned by %s. "
                              "Please first close this one to use this point of sale.") % session.user_id.name)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url':   '/pos/web/',
        }

class PaymentLine(models.Model):
    _name = 'payment.line'

    session_id = fields.Many2one('pos.session', string='工作记录')
    amount = fields.Float(u'总金额')
    pay_date = fields.Datetime(u'付款时间')
    pay_type_id = fields.Many2one(u'bank.account', u'付款方式')
    sell_id = fields.Many2one('sell.order', string='对应订单')