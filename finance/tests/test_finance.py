# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class test_voucher(TransactionCase):
   
    def test_approve(self):
        '''测试审核反审核报错'''
        voucher = self.env.ref('finance.voucher_1')
        #正常审批
        voucher.voucher_done()
        self.assertTrue(voucher.state == 'done')
        #已审批的凭证不可以删除
        with self.assertRaises(UserError):
            voucher.unlink()
        for line in voucher.line_ids:
            with self.assertRaises(UserError):
                line.unlink()
        #重复审批
        with self.assertRaises(UserError):
            voucher.voucher_done()
        #正常反审批
        voucher.voucher_draft()
        self.assertTrue(voucher.state == 'draft')
        #重复反审批
        with self.assertRaises(UserError):
            voucher.voucher_draft()
        #会计期间已关闭时的审批
        voucher.period_id.is_closed = True
        with self.assertRaises(UserError):
            voucher.voucher_done()
        #会计期间已关闭时的反审批
        voucher.period_id.is_closed = False
        voucher.voucher_done()
        voucher.period_id.is_closed = True
        with self.assertRaises(UserError):
            voucher.voucher_draft()

    def test_line_unlink(self):
        '''测试可正常删除未审核的凭证行'''
        voucher = self.env.ref('finance.voucher_1')
        for line in voucher.line_ids:
            line.unlink()
    def test_vourcher_write(self):
        period_id = self.env.ref('finance.period_201601')
        voucher = self.env.ref('finance.voucher_1')
        voucher.state = 'done'
        with self.assertRaises(UserError):
            voucher.write({'period_id':period_id.id})
        voucher.period_id.is_closed = True
        with self.assertRaises(UserError):
            voucher.write({'period_id':period_id.id})
        self.env.context= dict(self.env.context,**{"call_module":'checkout_wizard'})
        voucher.write({'period_id':period_id.id})

    def test_compute(self):
        '''新建凭证时计算字段加载'''
        voucher = self.env.ref('finance.voucher_1')
        self.assertTrue(voucher.period_id.name == u'2016年 第1期')
        self.assertTrue(voucher.amount_text == 50000.0)
        voucher.unlink()
    
    def test_check_balance(self):
        '''检查凭证借贷方合计平衡'''
        un_balance_voucher = self.env['voucher'].create({
            'line_ids':[(0,0,{
                             'account_id':self.env.ref('finance.account_cash').id,
                             'name':u'借贷方不平',
                             'debit':100,
                             })]
            })
        with self.assertRaises(ValidationError):
            un_balance_voucher.voucher_done()
    
    def test_check_line(self):
        '''检查凭证行'''
        # 没有凭证行
        voucher_no_line = self.env['voucher'].create({
            'line_ids': False
            })
        with self.assertRaises(ValidationError):
            voucher_no_line.voucher_done()
        # 检查借贷方都为0
        voucher_zero = self.env['voucher'].create({
            'line_ids':[(0,0,{
                             'account_id':self.env.ref('finance.account_cash').id,
                             'name':u'借贷方全为0',
                             })]
            })
        with self.assertRaises(ValidationError):
            voucher_zero.voucher_done()
        # 检查单行凭证行是否同时输入借和贷
        voucher = self.env['voucher'].create({
            'line_ids':[(0,0,{
                             'account_id':self.env.ref('finance.account_cash').id,
                             'name':u'借贷方同时输入',
                             'debit': 100,
                             'credit': 100,
                             })]
            })
        with self.assertRaises(ValidationError):
            voucher.voucher_done()

    def test_default_voucher_date(self):
        voucher_obj = self.env['voucher']
        voucher_rows = self.env['voucher'].search([])
        voucher_rows.unlink()
        setting_row = self.env['finance.config.settings'].create({
                "default_period_domain": "can",
                "default_reset_init_number": 1,
                "default_auto_reset": True,
                "default_reset_period": "month",
                "default_voucher_date": "today",})
        setting_row.execute()
        setting_row.write({'default_voucher_date':'last'})
        voucher_obj._default_voucher_date()
        voucher_obj.create({})

class test_period(TransactionCase):

    def test_get_period(self):
        period_obj = self.env['finance.period']
        if not period_obj.search([('year','=','2100'),
                                  ('month','=','6')]):
            with self.assertRaises(UserError):
                period_obj.get_period('2100-06-20')
        period_obj.get_year_fist_period_id()
        period_row = period_obj.search([('year','=','2016'),('month','=','10')])
        if not period_row:
            period_row = period_obj.create({'year':u'2016','month':u'10'})
        self.assertTrue(("2016-10-01","2016-10-31") ==period_obj.get_period_month_date_range(period_row))
        period_row.is_closed = True
        with self.assertRaises(UserError): #  得到对应时间的会计期间 ，期间已关闭
            period_obj.get_period('2016-10-10')
        # datetime_str = datetime.now().strftime("%Y-%m-%d")
        # datetime_str_list = datetime_str.split('-')
        # period_row = self.env['finance.period'].search(
        #     [('year', '=', datetime_str_list[0])])
        # if period_row: # 在相应的年份 会计期间不存在
        #     period_row.unlink()
        # period_obj.get_year_fist_period_id()

    def test_onchange_account_id(self):
        '''凭证行的科目变更影响到其他字段的可选值'''
        voucher = self.env.ref('finance.voucher_1')
        for line in voucher.line_ids:
            line.account_id = self.env.ref('finance.account_cash').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.account_goods').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.account_ar').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.account_ap').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.small_business_chart2211004').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.account_goods').id
            line.account_id.auxiliary_financing = 'goods'
            line.onchange_account_id()
            line.account_id.auxiliary_financing = 'partner'
            line.onchange_account_id()

        #这么写覆盖到了，但是这什么逻辑=。=
        self.env['voucher.line'].onchange_account_id()
                                                    

class test_finance_config_wizard (TransactionCase):

    def test_default(self):
        '''测试finance.config.settings默认值'''
        voucher_date_setting = self.env['finance.config.settings'].set_default_voucher_date()
        period_domain_setting = self.env['finance.config.settings'].set_default_period_domain()
        auto_reset_setting = self.env['finance.config.settings'].set_default_auto_reset()
        reset_period_setting = self.env['finance.config.settings'].set_default_reset_period()
        reset_init_number_setting = self.env['finance.config.settings'].set_default_reset_init_number()


class test_finance_account(TransactionCase):

    def setUp(self):
        super(test_finance_account, self).setUp()
        self.cash = self.env.ref('finance.account_cash')

    def test_name_get(self):
        name = self.cash.name_get()
        real_name = '%s %s' % (self.cash.code, self.cash.name)
        self.assertTrue(name[0][1] == real_name)

    def test_name_search(self):
        '''会计科目按名字和编号搜索'''
        result = self.env['finance.account'].name_search('库存现金')
        real_result = [(self.cash.id,
                        self.cash.code + ' ' + self.cash.name)]

        self.assertEqual(result, real_result)


    def test_get_smallest_code_account(self):
        account = self.env['finance.account']
        account.get_smallest_code_account()
    def test_get_max_code_account(self):
        account = self.env['finance.account']
        account.get_max_code_account()

class test_voucher_template_wizard(TransactionCase):
    def setUp(self):
        super(test_voucher_template_wizard, self).setUp()
        self.voucher = self.env.ref('finance.voucher_1')
        self.voucher_template_wizard = self.env['voucher.template.wizard'].create({
            'name':'测试模板','voucher_id':self.voucher.id,
        })
    def test_save_as_template(self):
        """凭证模板相关功能"""
        self.voucher_template_wizard.save_as_template()
        self.voucher_template_wizard.is_change_old_template = True
        old_template_id =self.env['voucher.template'].search([])[0].id if self.env['voucher.template'].search([]) else False
        self.voucher_template_wizard.old_template_id = old_template_id
        self.voucher_template_wizard.save_as_template()
    def test_onchange_template_id(self):
        """凭证上模板字段的onchange"""
        old_template_id = self.env['voucher.template'].search([])[0].id if self.env[
            'voucher.template'].search([]) else False
        self.voucher.template_id= old_template_id
        self.voucher.onchange_template_id()


class test_checkout_wizard(TransactionCase):
    def setUp(self):
        super(test_checkout_wizard, self).setUp()
    def test_recreate_voucher_name(self):
        checkout_wizard_obj = self.env['checkout.wizard']
        period_id = self.env.ref('finance.period_201601')
        setting_row = self.env['finance.config.settings'].create({'auto_reset':True,'reset_period':'year'})
        checkout_wizard_obj.recreate_voucher_name(period_id)
        print "+===="
