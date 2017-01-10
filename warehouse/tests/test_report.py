# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import operator


class TestReport(TransactionCase):
    def setUp(self):
        super(TestReport, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_whin3').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_whin1').date = '2016-02-06'
        self.env.ref('warehouse.wh_in_wh_in_attribute').date = '2016-02-06'

        # 产品    仓库  批号         数量   类型
        # 键鼠套装 总仓              96    入库
        # 网线    总仓              11928 入库
        # 网线    总仓              120   出库
        # 网线    上海仓            120   入库
        # 键盘    总仓  kb160000567 600   入库
        # 鼠标    总仓  ms160301    1     入库
        # 鼠标    总仓  ms160302    1     入库
        self.env['wh.in'].search([('name', '!=', 'WH/IN/16040004')]).approve_order()
        # 先盘点产品，保证网线数量充足
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.env['wh.internal'].search([]).approve_order()

        self.transceive_wizard = self.env['report.stock.transceive.wizard'].create({
                            'date_start': '2016-04-01',
                            'date_end': '2016-04-03'})

    def test_report_base(self):
        report_base = self.env['report.base'].create({})

        self.assertEqual(report_base.select_sql(), '')
        self.assertEqual(report_base.from_sql(), '')
        self.assertEqual(report_base.where_sql(), '')
        self.assertEqual(report_base.group_sql(), '')
        self.assertEqual(report_base.order_sql(), '')
        self.assertEqual(report_base.get_context(), {})
        self.assertEqual(report_base.collect_data_by_sql(), [])

    def test_open_report(self):
        # 测试商品收发明细表的wizard
        self.assertEqual(self.transceive_wizard.onchange_date(), {})

        self.transceive_wizard.date_end = '1999-09-09'
        results = self.transceive_wizard.onchange_date()
        real_results = {'warning': {
            'title': u'错误',
            'message': u'结束日期不可以小于开始日期'
        }, 'value': {'date_end': self.transceive_wizard.date_start}}

        self.assertEqual(results, real_results)
        self.assertEqual(self.transceive_wizard.open_report().get('res_model'), 'report.stock.transceive')
        # 测试wizard默认日期
        self.env['report.stock.transceive.wizard'].create({})

    def test_stock_transceive_search_read(self):
        stock_transceive = self.env['report.stock.transceive'].create({})
        self.transceive_wizard.date_start = '2016-02-01'
        context = self.transceive_wizard.open_report().get('context')

        real_results = [
            # 产品 仓库 出库数量 入库数量
            (u'键盘', u'总仓', 0, 600),
            (u'鼠标', u'总仓', 0, 2),
            (u'网线', u'总仓', 120, 12048),
            (u'网线', u'上海仓', 0, 120),
            (u'键鼠套装', u'总仓', 0, 96),
        ]
        results = stock_transceive.with_context(context).search_read(domain=[])
        length = stock_transceive.with_context(context).search_count(domain=[])
        self.assertEqual(len(results), len(real_results))
        self.assertEqual(len(results), length)

        instance = stock_transceive.with_context(context).browse(results[0].get('id'))
        self.assertEqual(instance.read(['warehouse'])[0].get('warehouse'), results[0].get('warehouse'))

        for result in results:
            result = (
                result.get('goods'),
                result.get('warehouse'),
                result.get('goods_qty_out'),
                result.get('goods_qty_in'),
            )
            self.assertTrue(result in real_results)

        stock_transceive.with_context(context).find_source_move_line()
