# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDbBackup(TransactionCase):

    def setUp(self):
        ''' 准备数据 '''
        super(TestDbBackup, self).setUp()
        self.obj = self.env.get('db.backup')
        # self.back = self.env.ref('auto_backup.backup_demo')

    def test_schedule_backup_pgtool(self):
        ''' 测试：数据库自动备份 '''
        self.obj.schedule_backup_pgtool()
