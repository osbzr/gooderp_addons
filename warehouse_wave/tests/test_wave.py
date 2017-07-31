# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class test_create_wave(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(test_create_wave, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.order.id)])

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
        order_1.sell_order_done()
        delivery_1 = self.env['sell.delivery'].search([('order_id', '=', order_1.id)])
        delivery_1.express_type = 'SF'
        with self.assertRaises(UserError):
            self.env['create.wave'].with_context({
                                                  'active_model': 'sell.delivery',
                                                  'active_ids': [self.delivery.id, delivery_1.id],
                                                  }).fields_view_get(None, 'form', False, False)

    def test_create_wave(self):
        ''' 测试 create_wave '''
        wave_wizard = self.env['create.wave'].with_context({
                                            'active_ids': self.delivery.id}).create({
                                            'active_model': 'sell.delivery',
                                             })
        wave_wizard.create_wave()

        # 请不要重复生成分拣货单
        with self.assertRaises(UserError):
            self.env['create.wave'].with_context({
                                                  'active_model': 'sell.delivery',
                                                  'active_ids': self.delivery.id,
                                                  }).fields_view_get(None, 'form', False, False)

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
        
        
class test_wave(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(test_wave, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.order.id)])
        
        self.wave_wizard = self.env['create.wave'].with_context({
                                            'active_ids': self.delivery.id}).create({
                                            'active_model': 'sell.delivery',
                                             })
        self.wave_wizard.create_wave()
        self.wave = self.env['wave'].search([])

    def test_report_wave(self):
        ''' 测试 report_wave'''
        self.wave[0].report_wave()

    def test_print_express_menu(self):
        ''' 测试 print_express_menu'''
        self.wave[0].print_express_menu()
        
    def test_unlink(self):
        ''' 测试 unlink'''
        self.wave[0].unlink()
        
class test_do_pack(TransactionCase):

    def setUp(self):
        ''' 准备基本数据 '''
        super(test_do_pack, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.order.id)])
        self.delivery.express_code = '123456'
        
        self.wave_wizard = self.env['create.wave'].with_context({
                                            'active_ids': self.delivery.id}).create({
                                            'active_model': 'sell.delivery',
                                             })
        self.wave_wizard.create_wave()
        self.wave = self.env['wave'].search([])
        
    def test_unlink(self):
        ''' 测试 unlink'''
        pack = self.env['do.pack'].create({ })
        pack.scan_barcode('123456', pack.id)
