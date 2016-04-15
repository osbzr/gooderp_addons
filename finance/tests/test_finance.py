# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm, ValidationError


class test_voucher(TransactionCase):

    def test_default(self):
        '''凭证号默认值'''
        self.env['voucher'].create({
                     })

    def test_compute(self):
        '''新建凭证时计算字段加载'''
        voucher = self.env.ref('finance.voucher_1')
        self.assertTrue(voucher.period_id.display_name == u'2016年 第4期')
        self.assertTrue(voucher.amount_text == '100.0')
    
    def test_check_balance(self):
        '''检查凭证借贷方合计平衡'''
        with self.assertRaises(ValidationError):
            self.env['voucher'].create({
            'document_word_id':self.env.ref('finance.document_word_1').id,
            'name':u'FV002734',
            'line_ids':[(0,0,{
                             'account_id':self.env.ref('finance.finance_account_1').id,
                             'name':u'借贷方不平',
                             'debit':100,
                             })]
            })
    
    def test_check_line(self):
        '''检查凭证行'''
        # 没有凭证行
        with self.assertRaises(ValidationError):
            self.env['voucher'].create({
            'document_word_id':self.env.ref('finance.document_word_1').id,
            'name':u'FV002734',
            'line_ids': False
            })
        # 检查借贷方都为0
        with self.assertRaises(ValidationError):
            self.env['voucher'].create({
            'document_word_id':self.env.ref('finance.document_word_1').id,
            'name':u'FV002734',
            'line_ids':[(0,0,{
                             'account_id':self.env.ref('finance.finance_account_1').id,
                             'name':u'借贷方全为0',
                             })]
            })
        with self.assertRaises(ValidationError):
            self.env['voucher'].create({
            'document_word_id':self.env.ref('finance.document_word_1').id,
            'name':u'FV002734',
            'line_ids':[(0,0,{
                             'account_id':self.env.ref('finance.finance_account_1').id,
                             'name':u'借贷方同时输入',
                             'debit': 100,
                             'credit': 100,
                             })]
            })

class test_period(TransactionCase):

    def test_get_period(self):
        period_obj = self.env['finance.period']
        if not period_obj.search([('year','=','2100'),
                                  ('month','=','6')]):
            with self.assertRaises(except_orm):
                period_obj.get_period('2100-06-20')
            
    def test_onchange_account_id(self):
        '''科目为空时的onchange'''
        voucher = self.env.ref('finance.voucher_1')
        for line in voucher.line_ids:
            line.account_id = self.env.ref('finance.finance_account_1').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.finance_account_2').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.finance_account_3').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.finance_account_4').id
            line.onchange_account_id()
            line.account_id = self.env.ref('finance.finance_account_5').id
            line.onchange_account_id()
        #这么写覆盖到了，但是这什么逻辑=。=
        self.env['voucher.line'].onchange_account_id()
                                                    

        