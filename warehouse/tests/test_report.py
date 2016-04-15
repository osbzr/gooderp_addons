# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm
import operator


class TestReport(TransactionCase):
    def setUp(self):
        super(TestReport, self).setUp()

        # 产品    仓库  批号         数量   类型
        # 键鼠套装 总仓              96    入库
        # 网线    总仓              11928 入库
        # 网线    总仓              120   出库
        # 网线    上海仓            120   入库
        # 键盘    总仓  kb160000567 600   入库
        # 鼠标    总仓  ms160301    1     入库
        # 鼠标    总仓  ms160302    1     入库
        self.env['wh.in'].search([('name', '!=', 'WH/IN/16040004')]).approve_order()
        self.env['wh.internal'].search([]).approve_order()

        self.track_wizard = self.env['report.lot.track.wizard'].create({})
        self.transceive_wizard = self.env['report.stock.transceive.wizard'].create({})
        self.collect_wizard = self.env['report.stock.transceive.collect.wizard'].create({})

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
        self.assertEqual(self.track_wizard.onchange_date()[0], {})

        self.track_wizard.date_end = '1999-09-09'
        results = self.track_wizard.onchange_date()[0]
        real_results = {'warning': {
            'title': u'错误',
            'message': u'结束日期不可以小于开始日期'
        }, 'value': {'date_end': self.track_wizard.date_start}}

        self.assertEqual(results, real_results)
        self.assertEqual(self.track_wizard.open_report().get('res_model'), 'report.lot.track')

        # 测试商品收发明细表的wizard
        self.assertEqual(self.transceive_wizard.onchange_date()[0], {})

        self.transceive_wizard.date_end = '1999-09-09'
        results = self.transceive_wizard.onchange_date()[0]
        real_results = {'warning': {
            'title': u'错误',
            'message': u'结束日期不可以小于开始日期'
        }, 'value': {'date_end': self.transceive_wizard.date_start}}

        self.assertEqual(results, real_results)
        self.assertEqual(self.transceive_wizard.open_report().get('res_model'), 'report.stock.transceive')

        # 测试商品收发汇总表的wizard
        self.assertEqual(self.collect_wizard.onchange_date()[0], {})

        self.collect_wizard.date_end = '1999-09-09'
        results = self.collect_wizard.onchange_date()[0]
        real_results = {'warning': {
            'title': u'错误',
            'message': u'结束日期不可以小于开始日期'
        }, 'value': {'date_end': self.collect_wizard.date_start}}

        self.assertEqual(results, real_results)
        self.assertEqual(self.collect_wizard.open_report().get('res_model'), 'report.stock.transceive.collect')

    def test_lot_track_search_read(self):
        lot_track = self.env['report.lot.track'].create({})
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
        with self.assertRaises(except_orm):
            domain = ['domain']
            lot_track.with_context(context).search_read(domain=domain)

        # domain条件中长度不为3的
        with self.assertRaises(except_orm):
            domain = [('goods', u'鼠标')]
            lot_track.with_context(context).search_read(domain=domain)

        # domain条件中使用不合法的操作符
        with self.assertRaises(except_orm):
            domain = [('goods', 'lg', u'鼠标')]
            lot_track.with_context(context).search_read(domain=domain)

    def test_lot_track_read_group(self):
        lot_track = self.env['report.lot.track'].create({})
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
        self.assertEqual(len(results), len(real_results))
        for result in results:
            result = (
                result.get('goods'),
                result.get('warehouse'),
                result.get('goods_qty_out'),
                result.get('goods_qty_in'),
            )
            self.assertTrue(result in real_results)

    def test_stock_transceive_collect_search_read(self):
        stock_transceive = self.env['report.stock.transceive.collect'].create({})
        context = self.collect_wizard.open_report().get('context')

        real_results = [
            # 产品 仓库 其他入库数量 调拨入库数量 盘盈数量 调拨出库数量
            (u'键盘', u'总仓', 0, 0, 600, 0),
            (u'鼠标', u'总仓', 0, 0, 2, 0),
            (u'网线', u'总仓', 48, 0, 12000, 120),
            (u'网线', u'上海仓', 0, 120, 0, 0),
            (u'键鼠套装', u'总仓', 96, 0, 0, 0),
        ]
        results = stock_transceive.with_context(context).search_read(domain=[])
        self.assertEqual(len(results), len(real_results))
        for result in results:
            result = (
                result.get('goods'),
                result.get('warehouse'),
                result.get('others_in_qty') or 0,
                result.get('internal_in_qty') or 0,
                result.get('overage_in_qty') or 0,
                result.get('internal_out_qty') or 0,
            )
            self.assertTrue(result in real_results)
