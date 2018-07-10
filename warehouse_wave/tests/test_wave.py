# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCreateWave(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(TestCreateWave, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.others_wh_in = self.env.ref('warehouse.wh_in_whin0')
        self.env.ref('warehouse.wh_move_line_14').location_id = self.env.ref(
            'warehouse.a001_location').id
        # 补足库存数量
        self.others_wh_in.approve_order()
        self.delivery.express_type = 'SF'

    def test_fields_view_get(self):
        ''' 测试 fields_view_get '''
        self.env['create.wave'].with_context({
            'active_model': 'sell.delivery',
            'active_ids': self.delivery.id,
        }).fields_view_get(None, 'form', False, False)

    def test_fields_view_get_diff_express_type(self):
        ''' 测试 fields_view_get 发货方式不一样的发货单不能生成同一拣货单 '''
        # 发货方式不一样的发货单不能生成同一拣货单
        self.delivery.express_type = 'YTO'
        order_1 = self.env.ref('sell.sell_order_1')
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search(
            [('order_id', '=', order_1.id)])
        delivery_1.express_type = 'SF'
        with self.assertRaises(UserError):
            self.env['create.wave'].with_context({
                'active_model': 'sell.delivery',
                'active_ids': [self.delivery.id, delivery_1.id],
            }).fields_view_get(None, 'form', False, False)

    def test_fields_view_get_diff_warehouse(self):
        ''' 测试 fields_view_get 仓库不一样的发货单不能生成同一拣货单 '''
        order_1 = self.env.ref('sell.sell_order_1')
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search(
            [('order_id', '=', order_1.id)])
        self.delivery.express_type = 'SF'
        delivery_1.express_type = 'SF'
        with self.assertRaises(UserError):
            self.env['create.wave'].with_context({
                'active_model': 'sell.delivery',
                'active_ids': [self.delivery.id, delivery_1.id],
            }).fields_view_get(None, 'form', False, False)

    def test_create_wave(self):
        ''' 测试 create_wave '''
        # goods from different locations, and the first location's qty is enough
        order_1 = self.env.ref('sell.sell_order_1')
        order_1.warehouse_id = self.env.ref('warehouse.hd_stock').id
        self.env.ref('sell.sell_order_line_1').goods_id = self.env.ref('goods.cable').id
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search([('order_id', '=', order_1.id)])
        others_wh_in = self.env.ref('warehouse.wh_in_whin3')
        others_in_line = self.env.ref('warehouse.wh_move_line_keyboard_mouse_in_2')
        others_in_line.location_id = self.env.ref('warehouse.b001_location').id
        others_in_line.goods_id = self.env.ref('goods.cable').id
        # 补足库存数量
        others_wh_in.approve_order()

        # wh_move_line_14 在库位 a001_location 上网线的数量是 12000
        a001_location = self.env.ref('warehouse.a001_location')
        self.assertEqual(a001_location.current_qty, 12000)
        b001_location = self.env.ref('warehouse.b001_location')
        self.assertEqual(b001_location.current_qty, 48)
        delivery_1.express_type = 'SF'

        wave_wizard = self.env['create.wave'].with_context({
            'active_ids': [self.delivery.id, delivery_1.id]}).create({
            'active_model': 'sell.delivery',
        })
        wave_wizard.create_wave()

        # 请不要重复生成分拣货单
        with self.assertRaises(UserError):
            self.env['create.wave'].with_context({
                'active_model': 'sell.delivery',
                'active_ids': self.delivery.id,
            }).fields_view_get(None, 'form', False, False)

    def test_create_wave_goods_from_different_location(self):
        ''' Test create_wave，goods from different locations, and each location's qty is not enough '''
        order_1 = self.env.ref('sell.sell_order_1')
        order_1.warehouse_id = self.env.ref('warehouse.hd_stock').id
        self.env.ref('sell.sell_order_line_1').goods_id = self.env.ref('goods.cable').id
        self.env.ref('sell.sell_order_line_1').quantity = 12010
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search(
            [('order_id', '=', order_1.id)])
        others_wh_in = self.env.ref('warehouse.wh_in_whin3')
        others_in_line = self.env.ref('warehouse.wh_move_line_keyboard_mouse_in_2')
        others_in_line.location_id = self.env.ref('warehouse.b001_location').id
        others_in_line.goods_id = self.env.ref('goods.cable').id
        # 补足库存数量
        others_wh_in.approve_order()

        a001_location = self.env.ref('warehouse.a001_location')
        self.assertEqual(a001_location.current_qty, 12000)
        b001_location = self.env.ref('warehouse.b001_location')
        self.assertEqual(b001_location.current_qty, 48)
        delivery_1.express_type = 'SF'

        wave_wizard = self.env['create.wave'].with_context({
            'active_ids': [self.delivery.id, delivery_1.id]}).create({
            'active_model': 'sell.delivery',
        })
        wave_wizard.create_wave()

    def test_create_wave_same_goods_line(self):
        ''' 测试 create_wave has same goods line'''
        self.delivery.line_out_ids = [(0, 0, {'goods_id': self.env.ref('goods.cable').id,
                                              'goods_qty': 1,
                                              'tax_rate': 17.0,
                                              'type': 'out'})]

        wave_wizard = self.env['create.wave'].with_context({
            'active_ids': self.delivery.id}).create({
                'active_model': 'sell.delivery',
            })
        wave_wizard.create_wave()

    def test_create_wave_add_loc_no_qty(self):
        ''' 测试 create_wave 给 拣货单行添加 库位，无产品'''
        self.others_wh_in.cancel_approved_order()

        self.env.ref('warehouse.wh_move_line_14').location_id = self.env.ref('warehouse.b001_location').id
        self.others_wh_in.approve_order()
        wave_wizard = self.env['create.wave'].with_context({
            'active_ids': self.delivery.id}).create({
                'active_model': 'sell.delivery',
            })
        wave_wizard.create_wave()

    def test_create_wave_add_loc_no_qty_raise_error(self):
        ''' 测试 create_wave 给 拣货单行添加 库位，无产品'''
        self.others_wh_in.cancel_approved_order()
        with self.assertRaises(UserError):
            self.env.ref('warehouse.wh_move_line_14').location_id = False
            self.others_wh_in.approve_order()

    def test_create_wave_goods_no_stock(self):
        ''' 测试 create_wave，发货单行存在 虚拟商品 '''
        order_1 = self.env.ref('sell.sell_order_1')
        self.env.ref('sell.sell_order_line_3').order_id = order_1.id
        self.env.ref('goods.cable').no_stock = True # sell_order_line_3 上的商品设置为 虚拟商品
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search([('order_id', '=', order_1.id)])
        delivery_1.express_type = 'SF'
        wave_wizard = self.env['create.wave'].with_context({'active_ids': delivery_1.id}).create({
            'active_model': 'sell.delivery',
        })
        # 勾选的订单缺货
        with self.assertRaises(UserError):
            wave_wizard.create_wave()

        # 发货单行存在 虚拟商品
        order_1.sell_order_draft()
        self.env.ref('sell.sell_order_line_1').order_id = self.order.id
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search([('order_id', '=', order_1.id)])
        delivery_1.express_type = 'SF'
        wave_wizard = self.env['create.wave'].with_context({'active_ids': delivery_1.id}).create({
            'active_model': 'sell.delivery',
        })
        wave_wizard.create_wave()


class TestWave(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(TestWave, self).setUp()
        # 补足库存数量
        self.env.ref('warehouse.wh_in_whin0').approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.env.ref('sell.sell_order_line_2_3').tax_rate = 0
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.express_type = 'SF'

        self.wave_wizard = self.env['create.wave'].with_context({
            'active_ids': self.delivery.id}).create({
                'active_model': 'sell.delivery',
            })
        self.wave_wizard.create_wave()
        self.wave = self.env['wave'].search([])

    def test_create_wave(self):
        ''' 测试 create_wave 库存不足报错'''
        self.order.sell_order_draft()
        # goods_id.no_stock 为 True
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        self.env.ref('sell.sell_order_line_1').order_id = self.order.id
        self.env.ref('goods.mouse').no_stock = True

        self.order.warehouse_id = self.env.ref('core.warehouse_general').id
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])

        self.wave_wizard = self.env['create.wave'].with_context({
            'active_ids': self.delivery.id}).create({
                'active_model': 'sell.delivery',
            })
        with self.assertRaises(UserError):
            self.wave_wizard.create_wave()

    def test_report_wave(self):
        ''' 测试 report_wave'''
        report_wave = self.wave[0].report_wave()
        # 调用 report_wave 类里的 render_html 方法
        self.env['report.warehouse_wave.report_wave_view'].render_html(
            report_wave['context']['active_ids'])

    def test_print_express_menu(self):
        ''' 测试 print_express_menu'''
        self.wave[0].print_express_menu()

    def test_print_package_list(self):
        ''' 测试 print_package_list'''
        self.wave[0].print_package_list()

    def test_delivery_list(self):
        ''' Test: delivery_list '''
        self.wave[0].delivery_list()

    def test_unlink(self):
        ''' 测试 wave unlink'''
        self.wave[0].unlink()

        order_3 = self.env.ref('sell.sell_order_3')
        self.env.ref('sell.sell_order_line_3').tax_rate = 0
        self.env.ref('sell.sell_order_line_3').quantity = 1
        self.env.ref('sell.sell_order_line_3').discount_amount = 0
        order_3.discount_amount = 0
        order_3.warehouse_id = self.env.ref('warehouse.hd_stock').id
        order_3.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search(
            [('order_id', '=', order_3.id)])
        delivery_1.date = '2016-01-02'
        delivery_1.express_code = '123456'
        delivery_1.express_type = 'SF'
        wave_wizard = self.env['create.wave'].with_context({
            'active_ids': delivery_1.id}).create({
                'active_model': 'sell.delivery',
            })
        wave_wizard.create_wave()
        wave_2 = self.env['wave'].search([])
        pack = self.env['do.pack'].create({})
        pack.scan_barcode('123456', pack.id)

        # 发货单已经打包发货,捡货单不允许删除
        self.env.ref('goods.cable').barcode = '000'
        pack.scan_barcode('000', pack.id)
        with self.assertRaises(UserError):
            wave_2.unlink()

    def test_move_unlink(self):
        ''' test move unlink '''
        self.delivery.unlink()


class TestDoPack(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(TestDoPack, self).setUp()
        # 补足库存数量
        self.env.ref('warehouse.wh_in_whin0').approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.env.ref('sell.sell_order_line_2_3').quantity = 1
        self.env.ref('sell.sell_order_line_2_3').discount_amount = 0
        self.order.discount_amount = 0
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.express_code = '123456'
        self.delivery.express_type = 'SF'

        self.wave_wizard = self.env['create.wave'].with_context({
            'active_ids': self.delivery.id}).create({
                'active_model': 'sell.delivery',
            })
        self.wave_wizard.create_wave()
        self.wave = self.env['wave'].search([])

    def test_unlink(self):
        ''' 测试 pack unlink'''
        pack = self.env['do.pack'].create({})
        pack.scan_barcode('123456', pack.id)
        pack.unlink()

        # 已打包完成，记录不能删除
        pack = self.env['do.pack'].create({})
        pack.scan_barcode('123456', pack.id)

        self.env.ref('goods.cable').barcode = '000'
        pack.scan_barcode('000', pack.id)
        with self.assertRaises(UserError):
            pack.unlink()

    def test_scan_one_barcode(self):
        ''' 对于一个条码的处理,请先扫描快递面单 '''
        pack = self.env['do.pack'].create({})
        with self.assertRaises(UserError):
            pack.scan_one_barcode('123456', pack)

    def test_scan_barcode(self):
        ''' 测试 scan_barcode'''
        pack = self.env['do.pack'].create({})
        pack.scan_barcode('123456', pack.id)

        # 扫描产品在打包行上
        self.env.ref('goods.cable').barcode = '000'
        pack.scan_barcode('000', pack.id)
        # 已打包完成
        with self.assertRaises(UserError):
            pack.scan_barcode('000', pack.id)
        # 扫描产品不在打包行上
        self.env.ref('goods.cable').barcode = '111'
        with self.assertRaises(UserError):
            pack.scan_barcode('000', pack.id)

        # scan_one_barcode 请先扫描快递面单
        with self.assertRaises(UserError):
            pack.scan_barcode('6666', '')

        # 发货单已经打包完成
        pack = self.env['do.pack'].create({})
        with self.assertRaises(UserError):
            pack.scan_barcode('123456', pack.id)

    def test_scan_barcode_no_goods_line(self):
        ''' 测试 scan_barcode 扫描产品不在打包行上'''
        pack = self.env['do.pack'].create({})
        pack.scan_barcode('123456', pack.id)
        # 扫描产品不在打包行上
        self.env.ref('goods.cable').barcode = '111'
        with self.assertRaises(UserError):
            pack.scan_barcode('000', pack.id)

    def test_scan_barcode_needs_pack_qty(self):
        ''' 测试 scan_barcode 要求发货数量 < 打包数量 '''
        order_1 = self.env.ref('sell.sell_order_1')
        order_1.warehouse_id = self.env.ref('warehouse.hd_stock').id
        self.env.ref('sell.sell_order_line_1').quantity = 1
        self.env.ref('sell.sell_order_line_1').discount_amount = 0
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        order_1.discount_amount = 0
        self.env.ref('sell.sell_order_line_2_3').order_id = order_1.id
        self.env.ref('sell.sell_order_line_2_3').tax_rate = 0
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search(
            [('order_id', '=', order_1.id)])
        delivery_1.express_code = '8888'
        delivery_1.express_type = 'SF'
        wave_wizard = self.env['create.wave'].with_context({
            'active_ids': delivery_1.id}).create({
                'active_model': 'sell.delivery',
            })
        wave_wizard.create_wave()

        pack = self.env['do.pack'].create({})
        pack.scan_barcode('8888', pack.id)
        self.env.ref('goods.mouse').barcode = '222'
        pack.scan_barcode('222', pack.id)
        # 发货单要发货的商品已经充足
        with self.assertRaises(UserError):
            pack.scan_barcode('222', pack.id)

    def test_scan_barcode_is_pack_ok(self):
        ''' 测试 is_pack_ok, common.dialog.wizard '''
        order_3 = self.env.ref('sell.sell_order_3')
        order_3.warehouse_id = self.env.ref('warehouse.hd_stock').id
        self.env.ref('sell.sell_order_line_3').quantity = 1
        self.env.ref('sell.sell_order_line_3').discount_amount = 0
        self.env.ref('sell.sell_order_line_3').tax_rate = 0
        order_3.discount_amount = 0
        order_3.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search(
            [('order_id', '=', order_3.id)])
        delivery_1.express_code = '8888'
        delivery_1.express_type = 'SF'
        delivery_1.date = '2016-01-02'
        wave_wizard = self.env['create.wave'].with_context({ 'active_ids': delivery_1.id}).create({
            'active_model': 'sell.delivery'})
        wave_wizard.create_wave()

        self.env.ref('warehouse.wh_in_whin0').cancel_approved_order()
        pack = self.env['do.pack'].create({})
        pack.scan_barcode('8888', pack.id)
        self.env.ref('goods.cable').barcode = '222'
        pack.scan_barcode('222', pack.id)


class TestDeliveryExpressPackagePrint(TransactionCase):

    def setUp(self):
        ''' setUp Data '''
        super(TestDeliveryExpressPackagePrint, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])

    def test_button_print(self):
        ''' Test: button_print method, default_get method '''
        print_obj = self.env['delivery.express.package.print']
        print_obj.with_context({'active_ids': [self.delivery.id],
                                'express_info': True}).default_get(False)
        print_obj.with_context({'active_ids': [self.delivery.id],
                                'package_info': True}).default_get(False)
        print_obj.with_context({'active_ids': [self.delivery.id],
                                'express_info': True}).button_print()
        print_obj.with_context({'active_ids': [self.delivery.id],
                                'package_info': True}).button_print()
