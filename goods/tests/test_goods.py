# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase


class test_goods(TransactionCase):
    def test_goods(self):
        ''' 测试产品 '''
        # 单位转化，1捆网线12根
        res1 = self.env.ref('goods.cable').conversion_unit(10)
        self.assertEqual(res1 , 120)
        res2 = self.env.ref('goods.cable').anti_conversion_unit(12)
        self.assertEqual(res2, 1)

    def test_uom(self):
        cable = self.browse_ref('goods.cable')
        uom_pc = self.browse_ref('core.uom_pc')

        cable.uom_id = uom_pc
        cable.onchange_uom()

        self.assertEqual(cable.uos_id, cable.uom_id)
