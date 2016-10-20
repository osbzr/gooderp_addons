# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
class test_mobile(TransactionCase):
    def test_mobile_view(self):
        mobile_view = self.env['mobile.view']
        with self.assertRaises(UserError):
            mobile_view._check_many2one({'type': 'many2one'})
        mobile_view._check_many2one({'type': 'many2one', 'model': 'res.partner',
                                     'domain': "[('name','!=',False),('user_id','!=',False)]"})
        with self.assertRaises(ValueError):
            mobile_view._check_domain('res.partner',"(('name','!=',False),('user_id','!=',False))")
        with self.assertRaises(ValueError):
            mobile_view._check_domain('res.partner', "[('name','!='),('user_id','!=',False)]")
        with self.assertRaises(ValueError):
            mobile_view._check_domain('res.partner', "[('name','!=',False),('partner_id','!=',False)]")

        with self.assertRaises(UserError):
            mobile_view._check_selection({'type':'selection'})

        with self.assertRaises(ValueError):
            mobile_view._check_selection({'type': 'selection','selection':(1,2)})
        with self.assertRaises(ValueError):
            mobile_view._check_selection({'type': 'selection','selection':[(1,2,2)]})
        with self.assertRaises(ValueError):
            mobile_view._check_selection({'type': 'selection','selection':[1,2]})


    # def test_map_operator(self):
    #     mobile_view = self.env['mobile.view']
    #     mobile_view.map_operator('=')
    #     # mobile_view_row = mobile_view.create({'model':'res.partner','domain': "['|',('name','!=',False),('user_id','!=',False)]",'name':'test'})
    #     # mobile_view_row.column_type('user_id')
    #     # mobile_view_row.check_domain()