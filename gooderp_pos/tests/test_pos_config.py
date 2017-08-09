# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


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
        # self.pos_config.current_session_id.cash_control = True
        # self.pos_config.open_existing_session_cb_close()
