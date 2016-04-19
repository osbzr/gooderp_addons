# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class test_city_county(TransactionCase):
    '''测试省市县'''
    def test_onchange_partner(self):
        '''测试partner的onchange'''
        self.env['partner'].onchange_partner_id()
        partner_address = self.env['res.partner'].create(dict(name = 'jd.address',
                                                               email = 'd@d',
                                                               ))
        self.env.ref('core.jd').partner_address = partner_address.id
        self.env.ref('core.jd').onchange_partner_id()
