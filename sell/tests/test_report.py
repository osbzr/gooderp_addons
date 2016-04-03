# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_report(TransactionCase):
    def setUp(self):
        super(test_report, self).setUp()
        ''' 准备报表数据 '''
        order = self.env.ref('sell.sell_order_1')
        order.sell_order_done()
        receipt = self.env['sell.delivery'].search([('order_id','=',order.id)])
        #receipt.sell_delivery_done()
        
    def test_report(self):
        ''' 测试销售报表 '''
        
        '''
        # 执行向导
        track = self.env['sell.order.track.wizard'].create({})
        # 输出报表
        track.button_ok()
        
        # 执行向导
        detail = self.env['sell.order.detail.wizard'].create({})
        # 输出报表
        detail.button_ok()
        '''
        
        # 执行向导
        statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': 
                     self.env.ref('sell.sell_order_1').partner_id.id})
        # 输出报表
        statement.partner_statements_without_goods()
        statement.partner_statements_with_goods()
        
        