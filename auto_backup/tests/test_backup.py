# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
import socket


class TestDbBackup(TransactionCase):

    def setUp(self):
        ''' 准备数据 '''
        super(TestDbBackup, self).setUp()
        self.ip = socket.gethostbyname("www.gooderp.org")
        confs = self.env['db.backup'].get_db_list(host="%s" % self.ip, port='8888')
        name = confs and confs[0] or 'gooderp'
        self.backup = self.env['db.backup'].create({
            "name": "%s" % name,
            "host": "%s" % self.ip,
            "port": "8888",
        })
