# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestDbBackup(TransactionCase):

    def setUp(self):
        super(TestDbBackup, self).setUp()
        self.obj = self.env.get('db.backup')
        self.back = self.env.ref('auto_backup.backup_demo')
    '''
    def test_schedule_backup(self):
        self.obj.schedule_backup()

    def test_schedule_backup_pgtool(self): 
        self.obj.schedule_backup_pgtool()
    '''
