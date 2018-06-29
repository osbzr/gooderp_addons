# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestGoodsClass(TransactionCase):

    def setUp(self):
        ''' 基本数据 '''
        super(TestGoodsClass, self).setUp()
        self.fruits_vegetables = self.env.ref('goods.fruits_vegetables')
        self.partner_services = self.env.ref('goods.partner_services')

    def test_check_category_recursion(self):
        ''' 测试，创建循环分类'''
        self.fruits_vegetables.parent_id = self.partner_services.id
        with self.assertRaises(ValidationError):
            self.partner_services.parent_id = self.fruits_vegetables.id


class TestGoods(TransactionCase):

    def setUp(self):
        super(TestGoods, self).setUp()
        self.goods_mouse = self.env.ref('goods.mouse')

    def test_conversion_unit(self):
        ''' 单位转化，1捆网线12根  '''
        res1 = self.env.ref('goods.cable').conversion_unit(10)
        self.assertEqual(res1, 120)

    def test_anti_conversion_unit(self):
        ''' 单位转化，12根网线1捆  '''
        res2 = self.env.ref('goods.cable').anti_conversion_unit(12)
        self.assertEqual(res2, 1)

    def test_uom(self):
        cable = self.browse_ref('goods.cable')
        uom_pc = self.browse_ref('core.uom_pc')

        cable.uom_id = uom_pc
        cable.onchange_uom()

        self.assertEqual(cable.uos_id, cable.uom_id)

    def test_onchange_using_batch(self):
        '''当将管理批号的勾去掉后，自动将管理序列号的勾去掉'''
        self.goods_mouse.using_batch = True
        self.goods_mouse.force_batch_one = True
        self.goods_mouse.using_batch = False
        self.goods_mouse.onchange_using_batch()

        self.assertEqual(self.goods_mouse.force_batch_one, False)

    def test_unlink(self):
        ''' 删除商品其对应属性也删除  '''
        self.env.ref('goods.keyboard').unlink()
        with self.assertRaises(ValueError):
            self.env.ref('goods.attribute_value_white')

    def test_name_search(self):
        '''测试goods的按名字和编号搜索'''
        mouse = self.env.ref('goods.mouse')
        # 使用name来搜索键盘
        result = self.env['goods'].name_search('鼠标')
        real_result = [(mouse.id,
                        mouse.code + '_' + mouse.name)]

        self.assertEqual(result, real_result)

        # 使用code来搜索键盘
        result = self.env['goods'].name_search('001')
        self.assertEqual(result, real_result)

        # goods name_search code ilike name
        self.env['goods'].name_search('00%')

    def test_create(self):
        '''导入商品时，如果辅助单位为空，则用计量单位来填充它'''
        goods = self.env['goods'].create({
            'name': u'显示器',
            'category_id': self.env.ref('core.goods_category_1').id,
            'uom_id': self.env.ref('core.uom_pc').id,
            'conversion': 1,
            'cost': 1000,
        })
        self.assertTrue(goods.uos_id.id == self.env.ref('core.uom_pc').id)

    def test_copy(self):
        '''测试商品的复制功能'''
        mouse = self.goods_mouse.copy()
        self.assertEqual(u'鼠标 (copy)', mouse.name)

    def test_get_tax_rate(self):
        ''' Test: get tax rate '''
        fruits_vegetables = self.env.ref('goods.fruits_vegetables')
        partner_services = self.env.ref('goods.partner_services')
        fruits_vegetables.parent_id = partner_services.id

        # 取产品上的税率
        fruits_vegetables.tax_rate = 10.0
        self.goods_mouse.goods_class_id = fruits_vegetables.id
        mouse_tax_rate = self.goods_mouse.get_tax_rate(self.goods_mouse, False, 'buy')
        self.assertEqual(mouse_tax_rate, 10.0)

        # 取末级 产品分类 上的税率
        fruits_vegetables.tax_rate = False
        partner_services.tax_rate = 11.0
        mouse_tax_rate = self.goods_mouse.get_tax_rate(self.goods_mouse, False, 'buy')
        self.assertEqual(mouse_tax_rate, 11.0)

        # 逐级取 产品分类 上的 税率
        partner_services.tax_rate = False
        goods_class_first = self.env['goods.class'].create({
            'name': '顶级分类',
            'tax_rate': 12.0
        })
        partner_services.parent_id = goods_class_first.id
        mouse_tax_rate = self.goods_mouse.get_tax_rate(self.goods_mouse, False, 'buy')
        self.assertEqual(mouse_tax_rate, 12.0)

        # no goods
        self.goods_mouse.get_tax_rate(False, False, 'buy')


class TestAttributes(TransactionCase):

    def test_ean_search(self):
        '''测试goods的按ean搜索'''
        iphone_value_white = self.env.ref('goods.iphone_value_white')
        result = self.env['attribute'].name_search('12345678987')
        real_result = [(iphone_value_white.id,
                        iphone_value_white.value_id.name)]
        self.assertEqual(result, real_result)

        # return super
        self.env['attribute'].name_search('123')

    def test_check_value_ids(self):
        '''属性值的类别不能相同'''
        # if 语句
        iphone_white = self.env.ref('goods.iphone_white')
        iphone_white.check_value_ids()

        # else 语句
        new_att = self.env['attribute.value'].create({
            'attribute_id': self.env.ref('goods.iphone_white').id,
            'category_id': self.env.ref('goods.attribute_color').id,
            'value_id': self.env.ref('goods.white').id, })

        with self.assertRaises(ValidationError):
            self.env.ref('goods.iphone').attribute_ids.write({'value_ids': [(4, 0, new_att.id)]})
