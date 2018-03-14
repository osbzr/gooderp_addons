# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
import socket


class TestDbBackup(TransactionCase):

    def setUp(self):
        ''' setUp Data '''
        super(TestDbBackup, self).setUp()
        self.ip = socket.gethostbyname("www.gooderp.org")
        confs = self.env['db.backup'].get_db_list(host="%s" % self.ip, port='8888')
        name = confs and confs[0] or 'gooderp'
        self.backup = self.env['db.backup'].create({
            "name": "%s" % name,
            "host": "%s" % self.ip,
            "port": "8888",
        })

    def test_schedule_backup(self):
        ''' Test：Database atuo backup '''
        self.backup.schedule_backup()

    def test_schedule_backup_pgtool(self):
        ''' Test：Database atuo backup '''
        self.backup.schedule_backup_pgtool()
