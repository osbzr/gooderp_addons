# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class TestWarehouse(TransactionCase):
    def setUp(self):
        super(TestWarehouse, self).setUp()
        self.hd_warehouse = self.browse_ref('warehouse.hd_stock')
        self.sh_warehouse = self.browse_ref('warehouse.sh_stock')

        self.internal = self.browse_ref('warehouse.wh_internal_whint0')
        self.overage_in = self.browse_ref('warehouse.wh_in_whin0')

        # 产品 仓库 数量     成本
        # 鼠标 总仓 2.0     93.6
        # 键盘 总仓 600.0   56160.0
        # 网线 总仓 11880.0 1111968.0
        # 网线 上海 120.0   11232.0
        self.overage_in.approve_order()
        self.internal.approve_order()

    def test_stock(self):
        hd_real_results = [
            {'goods': u'鼠标', 'subtotal': 93.6, 'qty': 2.0},
            {'goods': u'键盘', 'subtotal': 56160.0, 'qty': 600.0},
            {'goods': u'网线', 'subtotal': 1111968.0, 'qty': 11880.0},
        ]

        sh_real_results = [
            {'goods': u'网线', 'subtotal': 11232.0, 'qty': 120.0},
        ]

        for result in self.hd_warehouse.get_stock_qty():
            self.assertTrue(result in hd_real_results)

        self.assertEqual(self.sh_warehouse.get_stock_qty(), sh_real_results)

    def test_name_search(self):
        result = self.env['warehouse'].name_search('总仓')
        real_result = [(self.hd_warehouse.id, '[%s]%s' % (
            self.hd_warehouse.code, self.hd_warehouse.name))]

        self.assertEqual(result, real_result)

        with self.assertRaises(except_orm):
            self.env['warehouse'].get_warehouse_by_type('error')

        # 临时在warehouse的类型中添加一个error类型的错误，让它跳过类型检测的异常
        # 此时在数据库中找不到该类型的仓库，应该报错
        self.env['warehouse'].WAREHOUSE_TYPE.append('error')
        with self.assertRaises(except_orm):
            self.env['warehouse'].get_warehouse_by_type('error')
