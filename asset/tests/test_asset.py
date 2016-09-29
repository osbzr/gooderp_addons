# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_asset(TransactionCase):

    def setUp(self):
        super(test_asset, self).setUp()
        self.asset = self.env.ref('asset.asset_car')

    def test_unlink(self):
        '''测试删除已审核的固定资产'''
        asset = self.asset.copy()
        self.asset.asset_done()
        with self.assertRaises(except_orm):
            self.asset.unlink()
        # 删除草稿状态的固定资产
        asset.unlink()

    def test_onchange(self):
        '''资产相关科目由资产类别带出'''
        self.asset.category_id = self.env.ref('asset.house')
        self.onchange_category_id()
