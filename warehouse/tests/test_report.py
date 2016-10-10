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

        self.track_wizard = self.env['report.lot.track.wizard'].create({
                            'date_start': '2016-04-01',
                            'date_end': '2016-04-03'})
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
        # 测试批号跟踪表的wizard
        self.assertEqual(self.track_wizard.onchange_date(), {})

        self.track_wizard.date_end = '1999-09-09'
        results = self.track_wizard.onchange_date()
        real_results = {'warning': {
            'title': u'错误',
            'message': u'结束日期不可以小于开始日期'
        }, 'value': {'date_end': self.track_wizard.date_start}}

        self.assertEqual(results, real_results)
        self.assertEqual(self.track_wizard.open_report().get('res_model'), 'report.lot.track')
        # 测试wizard默认日期
        self.env['report.lot.track.wizard'].create({})

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

    def test_lot_track_search_read(self):
        lot_track = self.env['report.lot.track'].create({})
        self.track_wizard.date_start = '2016-02-01'
        context = self.track_wizard.open_report().get('context')

        real_results = [
            (u'键盘', 'kb160000567', u'总仓', 600),
            (u'鼠标', 'ms160301', u'总仓', 1),
            (u'鼠标', 'ms160302', u'总仓', 1),
        ]
        results = lot_track.with_context(context).search_read(domain=[])
        self.assertEqual(len(results), len(real_results))
        for result in results:
            result = (
                result.get('goods'),
                result.get('lot'),
                result.get('warehouse'),
                result.get('qty')
            )
            self.assertTrue(result in real_results)

        domain = ['|', '|', ('lot', 'ilike', '301'), ('lot', '=', 'ms160301'), ('goods', '=', u'键盘')]
        real_results = [
            (u'键盘', 'kb160000567', u'总仓', 600),
            (u'鼠标', 'ms160301', u'总仓', 1),
        ]
        domain_results = lot_track.with_context(context).search_read(domain=domain, order='qty DESC')
        self.assertEqual(sorted(domain_results, key=operator.itemgetter('qty')), domain_results)

        domain_results = lot_track.with_context(context).search_read(domain=domain, order='qty ASC')
        self.assertEqual(sorted(domain_results, key=operator.itemgetter('qty'), reverse=True), domain_results)

        self.assertEqual(len(domain_results), len(real_results))
        for result in domain_results:
            result = (
                result.get('goods'),
                result.get('lot'),
                result.get('warehouse'),
                result.get('qty')
            )
            self.assertTrue(result in real_results)

        # domain条件中不是列表或元祖的
        with self.assertRaises(UserError):
            domain = ['domain']
            lot_track.with_context(context).search_read(domain=domain)

        # domain条件中长度不为3的
        with self.assertRaises(UserError):
            domain = [('goods', u'鼠标')]
            lot_track.with_context(context).search_read(domain=domain)

        # domain条件中使用不合法的操作符
        with self.assertRaises(UserError):
            domain = [('goods', 'lg', u'鼠标')]
            lot_track.with_context(context).search_read(domain=domain)

    def test_lot_track_read_group(self):
        lot_track = self.env['report.lot.track'].create({})
        self.track_wizard.date_start = '2016-02-01'
        context = self.track_wizard.open_report().get('context')

        results = lot_track.with_context(context).read_group([], [], groupby=['goods'])
        real_results = [
            (u'键盘', 600, 1),
            (u'鼠标', 2, 2),
        ]

        self.assertEqual(len(results), len(real_results))
        for result in results:
            result = (
                result.get('goods'),
                result.get('qty'),
                result.get('goods_count'),
            )
            self.assertTrue(result in real_results)

        results = lot_track.with_context(context).read_group([('lot', '=', 'ms160301')], [], groupby=['goods', 'warehouse'])
        real_results = [
            (u'鼠标', 1, 1, {'group_by': ['warehouse']}),
        ]

        self.assertEqual(len(results), len(real_results))
        for result in results:
            result = (
                result.get('goods'),
                result.get('qty'),
                result.get('goods_count'),
                result.get('__context'),
            )
            self.assertTrue(result in real_results)

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
