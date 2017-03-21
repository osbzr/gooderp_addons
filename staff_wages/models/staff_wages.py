# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError

READONLY_STATES = {
        'done': [('readonly', True)],
    }

change = [('time', u'计时'),
                      ('piece', u'计件'),
                      ('efficiency', u'计效')]

class staff_wages(models.Model):
    _name = 'staff.wages'
    _description = u'员工工资'
    _order = "name"

    @api.one
    @api.depends('date')
    def _compute_period_id(self):
        self.name = self.env['finance.period'].get_period(self.date)

    date = fields.Date(u'记帐日期', required=True, states=READONLY_STATES)
    name = fields.Many2one(
        'finance.period',
        u'会计期间',
        compute='_compute_period_id', ondelete='restrict', store=True)
    state = fields.Selection([('draft', u'草稿'),
                              ('done', u'已审核')], u'状态', default='draft')
    line_ids = fields.One2many('wages.line', 'order_id', u'工资明细行',states=READONLY_STATES)
    payment = fields.Many2one('bank.account', u'付款方式')
    other_money_order = fields.Many2one('other.money.order', u'对应付款单', readonly=True, ondelete='restrict',
                                 help=u'审核时生成的对应付款单', copy=False)
    voucher_id = fields.Many2one('voucher', u'计提工资凭证', readonly=True, ondelete='restrict', copy=False)
    change_voucher_id = fields.Many2one('voucher', u'修正计提凭证', readonly=True, ondelete='restrict', copy=False)
    note = fields.Char(u'备注',help=u'本月备注')
    totoal_wage = fields.Float(u'应发工资合计')
    totoal_endowment = fields.Float(u'应扣养老合计')
    totoal_health = fields.Float(u'应扣医疗合计')
    totoal_unemployment = fields.Float(u'应扣失业合计')
    totoal_housing_fund = fields.Float(u'应扣住房合计')
    totoal_personal_tax = fields.Float(u'应扣个税合计')
    totoal_amount = fields.Float(u'实发工资合计')

    @api.onchange('line_ids')
    def _total_amount_wage(self):
        #todo 测试onchange + compute
        self.totoal_amount = sum(line.amount_wage for line in self.line_ids)
        self.totoal_wage = sum(line.all_wage for line in self.line_ids)
        self.totoal_endowment = sum(line.endowment for line in self.line_ids)
        self.totoal_health = sum(line.health for line in self.line_ids)
        self.totoal_unemployment = sum(line.unemployment for line in self.line_ids)
        self.totoal_housing_fund = sum(line.housing_fund for line in self.line_ids)
        self.totoal_personal_tax = sum(line.personal_tax for line in self.line_ids)

    @api.one
    def staff_wages_confim(self):
        self.staff_wages_accrued()
        self._other_pay()
        self.state = 'done'

    @api.one
    def staff_wages_accrued(self):
        if self.change_voucher_id:
            #删除原来的change_voucher_id ,生成新的change_voucher_id
            change_voucher_id, self.change_voucher_id = self.change_voucher_id, False
            if change_voucher_id.state == 'done':
                change_voucher_id.voucher_draft()
            change_voucher_id.unlink()
            self.change_voucher()
        elif self.voucher_id:
            #生成change_voucher_id
            self.change_voucher()
        else:
            #生成voucher_id
            date = self.date
            vouch_obj = self.create_voucher(date)[0]
            self.write({'voucher_id': vouch_obj.id})

    @api.one
    def change_voucher(self):
        before_voucher = self.voucher_id
        date = fields.Date.context_today(self)
        change_voucher = self.create_voucher(date)[0]
        for change_line in change_voucher.line_ids:
            for before_line in before_voucher.line_ids:
                if change_line.account_id.id == before_line.account_id.id:
                    change_line.credit -= before_line.credit
                    change_line.debit -= before_line.debit
                    continue

        for change_line in change_voucher.line_ids:
            if change_line.credit == 0 and change_line.debit == 0:
                change_line.unlink()

        if not change_voucher.line_ids:
            change_voucher.unlink()
        else:
            self.write({'change_voucher_id': change_voucher.id})

    @api.one
    def create_voucher(self,date):
        if self.voucher_id and self.voucher_id.period_id == self.env['finance.period'].get_period(date):
            raise UserError(u'同一会计期间内请使用反计提')
        vouch_obj = self.env['voucher'].create({'date': date})
        credit_account = self.env.ref('staff_wages.staff_wages')
        res = {}
        for line in self.line_ids:
            staff = self.env['staff.contract'].search([('staff_id', '=', line.name.id)])
            debite_account = staff.job_id and staff.job_id.account_id.id or self.env.ref('finance.small_business_chart5602001').id
            if debite_account not in res:
                res[debite_account] = {'debit': 0}
            val = res[debite_account]
            val.update({'debit': val.get('debit') + line.all_wage,
                        'voucher_id': vouch_obj.id,
                        'account_id': debite_account,
                        'name': u'提本月工资'})
        #生成借方凭证行
        for account_id,val in res.iteritems():
            self.env['voucher.line'].create(dict(val,account_id = account_id))
        #生成贷方凭证行
        self.env['voucher.line'].create({'credit': self.totoal_wage,
                                         'voucher_id': vouch_obj.id,
                                         'account_id': credit_account.account_id.id,
                                         'name': u'提本月工资'})
        return vouch_obj

    @api.one
    def _other_pay(self):
        '''选择结算账户，生成其他支出单 '''
        staff_wages = self.env.ref('staff_wages.staff_wages')
        endowment = self.env.ref('staff_wages.endowment')
        unemployment = self.env.ref('staff_wages.unemployment')
        housing_fund = self.env.ref('staff_wages.housing_fund')
        health = self.env.ref('staff_wages.health')
        personal_tax = self.env.ref('staff_wages.personal_tax')

        other_money_order = self.with_context(type='other_pay').env['other.money.order'].create({
            'state': 'draft',
            'date': fields.Date.context_today(self),
            'bank_id': self.payment.id,
        })
        self.write({'other_money_order': other_money_order.id})
        self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': self.totoal_wage ,
            'category_id': staff_wages and staff_wages.id
        })
        if self.totoal_endowment:
            self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': -1 * self.totoal_endowment ,
            'category_id': endowment and endowment.id
        })
        if self.totoal_unemployment:
            self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': -1 * self.totoal_unemployment ,
            'category_id': unemployment and unemployment.id
        })
        if self.totoal_housing_fund:
            self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': -1 * self.totoal_housing_fund ,
            'category_id': housing_fund and housing_fund.id
        })
        if self.totoal_health:
            self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': -1 * self.totoal_health ,

            'category_id': health and health.id
        })
        if self.totoal_personal_tax:
            self.env['other.money.order.line'].create({
            'other_money_id': other_money_order.id ,
            'amount': -1 * self.totoal_personal_tax ,
            'category_id': personal_tax and personal_tax.id
        })
        return other_money_order

    @api.one
    def staff_wages_draft(self):
        if self.other_money_order:
            other_money_order, self.other_money_order = self.other_money_order, False
            if other_money_order.state == 'done':
                other_money_order.other_money_draft()
            other_money_order.unlink()
        self.state = 'draft'

    @api.one
    def staff_wages_unaccrued(self):
        if self.change_voucher_id:
            raise UserError(u'跨期间不可以使用计提，请使用计提来补充计提')
        if self.voucher_id:
            voucher_id, self.voucher_id = self.voucher_id, False
            if voucher_id.state == 'done':
                voucher_id.voucher_draft()
            voucher_id.unlink()
        self.state = 'draft'

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'不能删除已审核的单据(%s)'%self.period_id)

class wages_line(models.Model):
    _name = 'wages.line'
    _description = u'工资明细'

    name = fields.Many2one('staff', u'员工', required=True)
    date_number = fields.Float(u'出勤天数')
    basic_wage = fields.Float(u'基础工资')
    basic_date = fields.Float(u'基础天数')
    wage = fields.Float(u'出勤工资')
    add_hour = fields.Float(u'加班小时')
    add_wage = fields.Float(u'加班工资')
    other_wage = fields.Float(u'其它')
    all_wage = fields.Float(u'应发工资', store=True, compute='_all_wage_value')
    endowment = fields.Float(u'个人养老保险')
    health = fields.Float(u'个人医疗保险')
    unemployment = fields.Float(u'个人失业保险')
    housing_fund = fields.Float(u'个人住房公积金')
    personal_tax = fields.Float(u'个人所得税', store=True, compute='_personal_tax_value')
    amount_wage = fields.Float(u'实发工资', store=True, compute='_amount_wage_value')
    order_id = fields.Many2one('staff.wages', u'工资表', index=True,
                               required=True, ondelete='cascade')

    @api.onchange('date_number','basic_wage','basic_date')
    def change_wage_addhour(self):
        if self.date_number > 31 or self.basic_date > 31:
            #todo 修正月份日期判断
            raise UserError(u'一个月不可能超过31天')
        if self.date_number >= self.basic_date:
            self.add_hour = 8 * (self.date_number - self.basic_date)
            self.date_number = self.basic_date
            self.wage = self.basic_wage
            self.add_wage = round(2 * (self.add_hour / 8) *  (self.basic_wage /(self.basic_date or 1)),2)
        else:
            self.wage = round((self.date_number / self.basic_date or 1) * self.basic_wage,2)

    @api.onchange('add_hour')
    def change_add_wage(self):
        if self.add_hour:
            self.add_wage = round(2 * (self.add_hour / 8) *  (self.basic_wage /(self.basic_date or 1)),2)

    @api.onchange('name')
    def change_social_security(self):
        social_security = self.env['staff.contract'].search([('staff_id', '=', self.name.id)])
        self.basic_wage = social_security.basic_wage
        self.endowment = social_security.endowment
        self.health = social_security.health
        self.unemployment = social_security.unemployment
        self.housing_fund = social_security.housing_fund

    @api.one
    @api.depends('wage','add_wage','other_wage')
    def _all_wage_value(self):
        self.all_wage = self.wage + self.add_wage + self.other_wage

    @api.one
    @api.depends('all_wage','endowment','health','unemployment','housing_fund')
    def _personal_tax_value(self):
        total = self.all_wage - self.endowment - self.health - self.unemployment - self.housing_fund
        amount =  total - 3500
        if amount > 80000:
            self.personal_tax = round(amount * 0.45 - 13505, 2)
        elif amount >55000:
            self.personal_tax = round(amount * 0.35 - 5505, 2)
        elif amount >35000:
            self.personal_tax = round(amount * 0.3 - 2755, 2)
        elif amount >9000:
            self.personal_tax = round(amount * 0.25 - 1005, 2)
        elif amount >4500:
            self.personal_tax = round(amount * 0.2 - 555, 2)
        elif amount > 1500:
            self.personal_tax = round(amount * 0.1 - 105, 2)
        elif amount >=0 :
            self.personal_tax = round(amount * 0.03, 2)
        else :
            self.personal_tax = 0

    @api.one
    @api.depends('all_wage','endowment','health','unemployment','housing_fund','personal_tax')
    def _amount_wage_value(self):
        self.amount_wage = self.all_wage - self.endowment - self.health - self.unemployment - self.housing_fund - self.personal_tax

class add_wages_change(models.Model):
    _inherit = 'staff.contract'
    wages_change = fields.Selection(change, u'记工类型')