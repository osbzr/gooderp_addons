# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class test_pos_config(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_pos_config, self).setUp()
        self.pos_config = self.env.ref('gooderp_pos.pos_config_sell')

    def test_create(self):
        '''创建一个POS设置'''
        pos_config = self.env['pos.config'].create({
            'name': u'零售测试',
        })
        self.assertEqual(pos_config.sequence_id.name, u'POS Order 零售测试')

    def test_unlink(self):
        '''删除POS设置'''
        self.pos_config.unlink()

    def test_open_ui(self):
        '''打开一个session'''
        self.pos_config.open_ui()

    def test_open_existing_session_cb_close(self):
        ''''''
        self.pos_config.open_existing_session_cb_close()

    def test_open_session_cb(self):
        '''打开一个新会话'''
        self.pos_config.open_session_cb()
        self.pos_config.current_session_id.action_pos_session_open()
        self.assertEqual(self.pos_config.current_session_id.state, 'opened')
        self.pos_config.open_session_cb()

    def test_open_existing_session_cb(self):
        '''打开一个会话'''
        self.pos_config.open_existing_session_cb()

    def test_name_get(self):
        '''POS设置 name_get 方法'''
        name = self.pos_config.name_get()
        real_name = u'零售测试 (not used)'
        self.assertEqual(name[0][1], real_name)

        # 打开一个会话后，POS设置的名称变化
        self.pos_config.open_session_cb()
        name = self.pos_config.name_get()
        real_name = u'零售测试 (Administrator)'
        self.assertEqual(name[0][1], real_name)


class test_pos_session(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_pos_session, self).setUp()
        self.pos_config = self.env.ref('gooderp_pos.pos_config_sell')
        self.session = self.env['pos.session'].create({
            'config_id': self.pos_config.id,
        })

    def test_check_pos_config(self):
        '''不能创建两个活动会话'''
        self.pos_config.open_session_cb()
        with self.assertRaises(ValidationError):
            self.env['pos.session'].create({
                'config_id': self.pos_config.id,
            })

    def test_unlink(self):
        '''删除会话'''
        self.session.unlink()

    def test_login(self):
        '''登录'''
        self.session.login()
        self.assertEqual(self.session.login_number, 1)

    def test_open_frontend_cb(self):
        '''打开其他用户的会话'''
        self.session.open_frontend_cb()

        with self.assertRaises(UserError):
            self.session.user_id = self.env.ref('core.user_alice').id
            self.session.open_frontend_cb()


class test_res_users(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_res_users, self).setUp()
        self.user = self.env.ref('core.user_alice')

    def test_check_pin(self):
        """限制安全pin为数字"""
        self.user.pos_security_pin = '1234'
        with self.assertRaises(ValidationError):
            self.user.pos_security_pin = u'abcd'
