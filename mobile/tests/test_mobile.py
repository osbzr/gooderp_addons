# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
class test_mobile(TransactionCase):
    def test_mobile_view(self):
        mobile_view = self.env['mobile.view']
        with self.assertRaises(UserError):
            mobile_view._check_many2one({'type': 'many2one'})
        mobile_view._check_many2one({'type': 'many2one', 'model': 'res.partner',
                                     'domain': "[('name','!=',False),('user_id','!=',False)]"})
