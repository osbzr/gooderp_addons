# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MonthProductCost(models.Model):
    _name = 'month.product.cost'
    _order = 'period_id'
    period_id = fields.Many2one('finance.period', string='会计期间')
    goods_id = fields.Many2one('goods', string="产品")
    period_begin_qty = fields.Float(string='期初数量')
    period_begin_cost = fields.Float(string='期初成本')
    current_period_out_qty = fields.Float(string='本期出库量')
    current_period_out_cost = fields.Float(string='本期出库成本')
    current_period_in_qty = fields.Float(string='本期入库量')
    current_period_in_cost = fields.Float(string='本期入库成本')
    current_period_remaining_qty = fields.Float(string='本期剩余数量')
    current_period_remaining_cost = fields.Float(string='剩余数量成本')

    # 使用SQL来取得指定产品情况下的库存数量
    @api.multi
    def get_stock_qty(self, period_id):
        date_range = self.env['finance.period'].get_period_month_date_range(period_id)
        self.env.cr.execute('''
            SELECT line.goods_id as goods_id,
                   line.type as type,
                   sum(line.goods_qty) as qty,
                   sum(line.cost) as cost
            FROM wh_move_line line
            LEFT JOIN warehouse wh_dest ON line.warehouse_dest_id = wh_dest.id
            LEFT JOIN warehouse wh ON line.warehouse_id = wh.id
            WHERE  line.state = 'done'
              AND line.date >= '%s'
              AND line.date <= '%s'
              AND ((wh_dest.type='stock'AND wh.type!='stock') OR
                (wh_dest.type!='stock' AND wh.type='stock'))
            GROUP BY line.goods_id,line.type
        ''' % (date_range[0], date_range[1]))
        return self.env.cr.dictfetchall()

    @api.multi
    def get_goods_last_period_remaining_qty(self, period_id, goods_id):
        """
        :param period_id: 传入当前所需的期间，根据这个期间找到对应的上一个期间
        :param goods_id: 出入 goods 精确找到 上一期间 对应的 month.product.cost 记录
        :return: 让上一期间的 剩余数量，和剩余数量成本 以字典 形式返回
        """
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(period_id)
        month_product_cost_row = self.search([('period_id', '=', last_period.id), ('goods_id', '=', goods_id)])

        return {
            'current_period_remaining_qty': month_product_cost_row.current_period_remaining_qty or 0,
            'current_period_remaining_cost': month_product_cost_row.current_period_remaining_cost or 0
        }

    @api.multi
    def current_period_type_current_period(self, dcit_goods):
        """
        获得传入的dict的type 属性，根据属性，进行 返回不同的dict key值。
        :param dcit_goods: 含有type qty 和 cost 三个字段
        :return: 根据type 类型返回 {'current_period_in_qty':00 ,'current_period_in_cost':00 } 或者
        {'current_period_out_qty'：00,'current_period_out_cost' :00}
        """
        if dcit_goods.get('type') == 'in':
            res = {'current_period_in_qty': dcit_goods.get('qty', 0),
                   'current_period_in_cost': dcit_goods.get('cost', 0)}
        else:
            res = {'current_period_out_qty': dcit_goods.get('qty'),
                   'current_period_out_cost': dcit_goods.get('cost', 0)}
        return res

    @api.multi
    def month_remaining_qty_cost(self, goods_qty_cost):
        """
        根据前边数据据的 构造，在后边对字典里面的值进行处理。
        算出 本月的剩余的数量以放便，取下月的期初的数量，及余额
        :param month_remaining_qty_cost:
        :return: {'current_period_remaining_qty’： ×××,'current_period_remaining_cost':××× }
        """
        sum_goods_qty = goods_qty_cost.get('period_begin_qty', 0) - \
                        goods_qty_cost.get('current_period_out_qty', 0) + \
                        goods_qty_cost.get('current_period_in_qty', 0)
        sum_goods_cost =goods_qty_cost.get('period_begin_cost', 0) - \
                       goods_qty_cost.get('current_period_out_cost',0) + \
                        goods_qty_cost.get('current_period_in_cost',0)
        return {'current_period_remaining_qty': sum_goods_qty,
                'current_period_remaining_cost': sum_goods_cost}

    @api.multi
    def compute_balance_price(self, data_dcit):
        """
        本月该产品的结存单价 = （上月该产品的成本余额 + 本月入库成本 ）/ (上月数量余额 + 本月入库数量)
        则本月发出成本 = 结存单价 * 发出数量
        :param data_dcit:
        :return:月发出成本
        """
        company_row = self.env['res.company'].search([])
        if company_row and company_row[0].cost_method == 'average':
            balance_price = (data_dcit.get("period_begin_cost", 0) + data_dcit.get("current_period_in_cost", 0)) / \
                            (data_dcit.get("period_begin_qty", 0) + data_dcit.get("current_period_in_qty", 0))
            month_cost = balance_price * data_dcit.get("current_period_out_qty", 0)
        else:
            month_cost = data_dcit.get("current_period_out_cost", 0)
        return round(month_cost, 2)

    @api.multi
    def create_month_product_cost_voucher(self, period_id, month_product_cost_dict):
        voucher_line_data_list = []
        account_row = self.env.ref('finance.account_cost')
        all_balance_price = 0
        for create_vals in month_product_cost_dict.values():
            goods_row = self.env['goods'].browse(create_vals.get('goods_id'))
            current_period_out_cost = self.compute_balance_price(create_vals)
            if self.compute_balance_price(create_vals)!=0:
                voucher_line_data = {'name': u'发出成本', 'credit':current_period_out_cost,
                                     'account_id': goods_row.category_id.account_id.id,
                                     'goods_id': create_vals.get('goods_id')}
                voucher_line_data_list.append([0, 0, voucher_line_data.copy()])
            create_vals.update({'current_period_out_cost':current_period_out_cost})
            all_balance_price += self.compute_balance_price(create_vals)
            self.create(create_vals)
        if all_balance_price != 0:
            voucher_line_data_list.append(
                [0, 0, {'name': u'发出成本', 'account_id': account_row.id, 'debit': all_balance_price}])
        if voucher_line_data_list:
            voucher_id = self.env['voucher'].create({'period_id': period_id.id, 'line_ids': voucher_line_data_list,
                                                     'is_checkout':True})
            voucher_id.voucher_done()

    @api.multi
    def data_structure(self, list_dict_data, period_id):
        """

        :param list_dict_data:
        :param period_id:
        :return:
        """
        month_product_cost_dict = {}
        for dict_goods in list_dict_data:
            period_begin_qty_cost = self.get_goods_last_period_remaining_qty(period_id, dict_goods.get('goods_id'))
            vals = {}
            if dict_goods.get('goods_id') not in month_product_cost_dict:
                vals = {'goods_id': dict_goods.get('goods_id'), 'period_id': period_id.id,
                        'period_begin_qty': period_begin_qty_cost.get('current_period_remaining_qty', 0),
                        'period_begin_cost': period_begin_qty_cost.get('current_period_remaining_cost', 0)}
                vals.update(self.current_period_type_current_period(dict_goods))
                month_product_cost_dict.update({dict_goods.get('goods_id'): vals.copy()})
                month_product_cost_dict.get(dict_goods.get('goods_id')).update(self.month_remaining_qty_cost(
                    month_product_cost_dict.get(dict_goods.get('goods_id'))))
            else:
                vals.update(self.current_period_type_current_period(dict_goods))
                month_product_cost_dict.get(dict_goods.get('goods_id')).update(vals.copy())
                month_product_cost_dict.get(dict_goods.get('goods_id')).update(self.month_remaining_qty_cost(
                    month_product_cost_dict.get(dict_goods.get('goods_id'))))
        return month_product_cost_dict

    @api.multi
    def generate_issue_cost(self, period_id):
        """

        :param period_id:
        :return:
        """
        list_dict_data = self.get_stock_qty(period_id)
        issue_cost_exists = self.search([('period_id', '=', period_id.id)])
        issue_cost_exists.unlink()
        self.create_month_product_cost_voucher(period_id, self.data_structure(list_dict_data, period_id))


class CheckOutWizard(models.TransientModel):
    '''月末结账的向导'''
    _inherit = 'checkout.wizard'

    @api.multi
    def button_checkout(self):
        """

        :return:
        """
        if self.period_id:
            if self.env['ir.module.module'].sudo().search([('state', '=', 'installed'), ('name', '=', 'warehouse')]):
                self.env['month.product.cost'].generate_issue_cost(self.period_id)
        res = super(CheckOutWizard, self).button_checkout()
        return res
