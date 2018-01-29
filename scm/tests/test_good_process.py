# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestProcess(TransactionCase):

    def test_create(self):
        """新建审批配置规则，如果配置的模型有type字段而规则未输入type，保存时给出提示"""
        with self.assertRaises(ValidationError):
            self.env['good_process.process'].create({
                'model_id': self.env.ref('buy.model_buy_order').id,
            })
        # 审批规则必须唯一
        with self.assertRaises(ValidationError):
            self.env['good_process.process'].create({
                'model_id': self.env.ref('buy.model_buy_order').id,
                'type': 'buy'
            })


class TestMailThread(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestMailThread, self).setUp()
        self.approve_rule = self.browse_ref('scm.process_buy_order')  # 审批规则
        self.order = self.env.ref('buy.buy_order_1').copy()
        self.staff_admin = self.env.ref('staff.staff_1')
        self.user_demo = self.browse_ref('base.user_demo')

    def test_normal_case(self):
        """正常审批流程"""
        env2 = self.env(self.env.cr, self.user_demo.id, self.env.context)

        self.assertTrue(self.order._approve_state == u'已提交')
        # 经理审批
        self.order.with_env(env2).good_process_approve(
            self.order.id, self.order._name)
        self.assertTrue(self.order._approve_state == u'审批中')
        # 自己先拒绝
        self.order.good_process_refused(self.order.id, self.order._name)
        # 经理重新审批
        self.order.with_env(env2).good_process_approve(
            self.order.id, self.order._name)
        # 自己审批
        self.order.good_process_approve(self.order.id, self.order._name)
        self.assertTrue(self.order._approve_state == u'已审批')
        self.order.buy_order_done()
        self.order.buy_order_draft()
  #      self.order.unlink()   暂时注释掉

    def test_approver_sequence(self):
        """审批顺序"""
        group_1 = self.env.ref('scm.group_process_buy_order')
        # 自己审批
        result = self.order.good_process_approve(
            self.order.id, self.order._name)
        self.assertTrue(result[0] == u'您不是这张单据的下一个审批者')

        # admin的经理改为空，将用户组1中的用户改为Alice,admin去审批
        self.staff_admin.parent_id = False  # TODO:不起作用
        group_1.write(
            {'users': [(6, 0, [self.env.ref('core.user_alice').id])]})
        res = self.order.good_process_approve(self.order.id, self.order._name)
        self.assertTrue(res[0] == u'您不是这张单据的下一个审批者')

    def test_refuser_sequence(self):
        """拒绝顺序"""
        env2 = self.env(self.env.cr, self.user_demo.id, self.env.context)
        # 自己拒绝
        result = self.order.good_process_refused(
            self.order.id, self.order._name)
        self.assertTrue(result[0] == u'您是第一批需要审批的人，无需拒绝！')

        # 经理和自己审批之后
        self.order.with_env(env2).good_process_approve(
            self.order.id, self.order._name)
        self.order.good_process_approve(self.order.id, self.order._name)
        res = self.order.good_process_refused(self.order.id, self.order._name)
        self.assertTrue(res[0] == u'已经通过不能拒绝！')

    def test_unlink(self):
        """级联删除"""
        self.order.unlink()

    def test_write(self):
        """write 审批异常流程"""
        env2 = self.env(self.env.cr, self.user_demo.id, self.env.context)

        # 已提交时审核报错
        self.assertTrue(self.order._approve_state == u'已提交')
        with self.assertRaises(ValidationError):
            self.order.buy_order_done()
        # 经理审批，审批中审核报错
        self.order.with_env(env2).good_process_approve(
            self.order.id, self.order._name)
        self.assertTrue(self.order._approve_state == u'审批中')
        with self.assertRaises(ValidationError):
            self.order.buy_order_done()
        # 审批中修改其他字段报错，不可删除
        with self.assertRaises(ValidationError):
            self.order.date = '2017-04-19'
        with self.assertRaises(ValidationError):
            self.order.unlink()
        # 已审批不可修改,不可删除
        self.order.good_process_approve(self.order.id, self.order._name)
        with self.assertRaises(ValidationError):
            self.order.date = '2017-04-19'
        with self.assertRaises(ValidationError):
            self.order.unlink()
        # 已审核的单据不可删除
        self.order.buy_order_done()
        with self.assertRaises(ValidationError):
            self.order.unlink()


class TestApprover(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestApprover, self).setUp()
        self.approve_rule = self.browse_ref('scm.process_buy_order')  # 审批规则
        self.order = self.env.ref('buy.buy_order_1').copy()
        self.user_demo = self.browse_ref('base.user_demo')

    def test_goto(self):
        """查看并处理"""
        env2 = self.env(self.env.cr, self.user_demo.id, self.env.context)
        self.order.with_env(env2)._to_approver_ids[0].goto()

        process = self.env['good_process.process'].create({
            'model_id': self.env.ref('buy.model_buy_receipt').id,
            'type': 'out',
            'is_department_approve': True
        })
        self.env['good_process.process_line'].create({
            'process_id': process.id,
            'sequence': 0,
            'group_id': self.env.ref('scm.group_process_buy_order').id,
            'is_all_approve': True})

        env2 = self.env(self.env.cr, self.user_demo.id, self.env.context)
        receipt = self.env.ref('buy.buy_receipt_return_1').copy()
        if receipt._to_approver_ids:
            receipt.with_env(env2)._to_approver_ids[0].goto()
