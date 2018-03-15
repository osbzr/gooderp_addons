# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
import socket


class TestDbBackup(TransactionCase):

    def setUp(self):
        ''' setUp Data '''
        super(TestDbBackup, self).setUp()
        self.backup = self.env.ref('auto_backup.backup_demo')

    def test_schedule_backup(self):
        ''' Test：Database atuo backup '''
        self.backup.schedule_backup()

    def test_schedule_backup_pgtool(self):
        ''' Test：Database atuo backup '''
        self.backup.schedule_backup_pgtool()
