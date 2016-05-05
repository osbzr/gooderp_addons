# -*- coding: utf-8 -*-

from datetime import date
from openerp import models, fields, api
from openerp.exceptions import except_orm

class checkout_wizard(models.TransientModel):
    '''月末结账的向导'''
    _name = 'checkout.wizard'

    period_id = fields.Many2one('finance.period',u'结账会计期间')
    date = fields.Date(u'生成凭证日期',required=True)

    @api.multi
    @api.onchange('date')
    def onchange_period_id(self):
        self.period_id = self.env['finance.period'].get_period(self.date)

    @api.multi
    def button_checkout(self):
        if self.period_id:
            last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(self.period_id)
            if last_period:
                if not last_period.is_closed:
                    raise except_orm(u'错误', u'上一个期间%s未结账' % last_period.name)
            if self.period_id.is_closed:
                raise except_orm(u'错误', u'本期间已结账')
            else:
                voucher_obj = self.env['voucher']
                voucher_ids = voucher_obj.search([('period_id','=',self.period_id.id)])
                i=0
                for voucher_id in voucher_ids:
                    if voucher_id.state != 'done':
                        i += 1
                if i != 0:
                    raise except_orm(u'错误', u'该期间有%s张凭证未审核' % i)
                else:
                    voucher_line = [] #生成的结账凭证行
                    account_obj = self.env['finance.account']
                    company_obj = self.env['res.company']
                    voucher_line_obj = self.env['voucher.line']
                    revenue_account_ids = account_obj.search([('costs_types','=','in')]) #收入类科目
                    expense_account_ids = account_obj.search([('costs_types','=','out')]) #费用类科目
                    revenue_total=0 #收入类科目合计
                    expense_total=0 #费用类科目合计
                    for revenue_account_id in revenue_account_ids:
                        voucher_line_ids = voucher_line_obj.search([
                                            ('account_id','=',revenue_account_id.id),
                                            ('voucher_id.period_id','=',self.period_id.id)])
                        credit_total = 0
                        for voucher_line_id in voucher_line_ids:
                            credit_total += voucher_line_id.credit
                        revenue_total += credit_total
                        if credit_total!= 0:
                            res={
                                 'name':u'月末结账',
                                 'account_id':revenue_account_id.id,
                                 'debit':credit_total,
                                 'credit':0,
                                 }
                            voucher_line.append(res)
                    for expense_account_id in expense_account_ids:
                        voucher_line_ids = voucher_line_obj.search([
                                            ('account_id','=',expense_account_id.id),
                                            ('voucher_id.period_id','=',self.period_id.id)])
                        debit_total = 0
                        for voucher_line_id in voucher_line_ids:
                            debit_total += voucher_line_id.debit
                        expense_total += debit_total
                        if debit_total != 0:
                            res={
                                 'name':u'月末结账',
                                 'account_id':expense_account_id.id,
                                 'debit':0,
                                 'credit':debit_total,
                                 }
                            voucher_line.append(res)
                    #利润结余
                    year_profit_account = company_obj.search([])[0].profit_account
                    remain_account = company_obj.search([])[0].remain_account
                    if not year_profit_account:
                        raise except_orm(u'错误', u'公司本年利润科目未配置')
                    if not remain_account:
                        raise except_orm(u'错误', u'公司未分配利润科目未配置')
                    if (revenue_total - expense_total) > 0:
                        res={
                             'name':u'利润结余',
                             'account_id':year_profit_account.id,
                             'debit':0,
                             'credit':revenue_total - expense_total,
                             }
                        voucher_line.append(res)
                    if (revenue_total - expense_total) < 0:
                        res={
                             'name':u'利润结余',
                             'account_id':year_profit_account.id,
                             'debit':expense_total - revenue_total,
                             'credit':0,
                             }
                        voucher_line.append(res)
                    #生成凭证
                    valus={
                           'is_checkout':True,
                           'date':self.date,
                           'line_ids':[
                                    (0, 0, line) for line in voucher_line],
                           }
                    voucher = voucher_obj.create(valus)
                    voucher.voucher_done()
                if self.period_id.month == '12':
                    year_profit_ids = voucher_line_obj.search([
                                        ('account_id','=',year_profit_account.id),
                                        ('voucher_id.period_id','=',self.period_id.id)])
                    year_total=0
                    for year_profit_id in year_profit_ids:
                        year_total += (year_profit_id.credit - year_profit_id.debit)
                    year_line_ids=[{
                         'name':u'年度结余',
                         'account_id':remain_account.id,
                         'debit':0,
                         'credit':year_total,
                         },{
                         'name':u'年度结余',
                         'account_id':year_profit_account.id,
                         'debit':year_total,
                         'credit':0,
                            }]
                    value={'is_checkout':True,
                           'date':self.date,
                           'line_ids':[
                                    (0, 0, line) for line in year_line_ids],
                           }
                    year_account = voucher_obj.create(value)
                    year_account.voucher_done()
                #生成科目余额表
                trial_wizard = self.env['create.trial.balance.wizard'].create({
                        'period_id':self.period_id.id,
                                                                })
                trial_wizard.create_trial_balance()
                #关闭会计期间
                self.period_id.is_closed = True
                #如果下一个会计期间没有，则创建。
                next_period = self.env['create.trial.balance.wizard'].compute_next_period_id(self.period_id)
                if not next_period:
                    if self.period_id.month == '12':
                        self.env['finance.period'].create({'year':str(int(self.period_id.year) +1),
                                                           'month':'1',})
                    else:
                        self.env['finance.period'].create({'year':self.period_id.year,
                                                           'month':str(int(self.period_id.month) + 1),})
                #显示凭证
                view = self.env.ref('finance.voucher_form')
                return {
                    'name': u'月末结账',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'views': [(view.id, 'form')],
                    'res_model': 'voucher',
                    'type': 'ir.actions.act_window',
                    'res_id': voucher.id,
                    'limit': 300,
                }

    @api.multi
    def button_counter_checkout(self):
        if self.period_id:
            if not self.period_id.is_closed:
                raise except_orm(u'错误', u'本期间未结账')
            else:
                self.period_id.is_closed = False
                voucher_ids = self.env['voucher'].search([('is_checkout','=',True),
                                                          ('period_id','=',self.period_id.id)])
                for voucher_id in voucher_ids:
                    voucher_id.voucher_draft()
                    voucher_id.unlink()
        return