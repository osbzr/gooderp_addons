# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class test_process(TransactionCase):

    def test_create(self):
        """新建审批配置规则，如果配置的模型有type字段而规则未输入type，保存时给出提示"""
        with self.assertRaises(ValidationError):
            self.env['good_process.process'].create({
                'model_id': self.env.ref('buy.model_buy_order').id,
            })

class test_mail_thread(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_mail_thread, self).setUp()
        self.approve_rule = self.browse_ref('scm.process_buy_order') # 审批规则
        self.order = self.env.ref('buy.buy_order_1').copy()

    def test_normal_case(self):
        """正常审批流程"""
        user_demo = self.browse_ref('base.user_demo')
        env2 = self.env(self.env.cr, user_demo.id, self.env.context)

        self.assertTrue(self.order._approve_state == u'已提交')
        # 经理审批
        self.order.with_env(env2).good_process_approve(self.order.id, self.order._name)
        self.assertTrue(self.order._approve_state == u'审批中')
        # 自己先拒绝
        self.order.good_process_refused(self.order.id, self.order._name)
        # 经理重新审批
        self.order.with_env(env2).good_process_approve(self.order.id, self.order._name)
        # 自己审批
        self.order.good_process_approve(self.order.id, self.order._name)
        self.assertTrue(self.order._approve_state == u'已审批')
        self.order.buy_order_done()
        self.order.buy_order_draft()
        self.order.unlink()

