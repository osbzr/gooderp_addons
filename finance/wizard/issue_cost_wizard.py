# -*- coding: utf-8 -*-

from openerp import models, fields, api


class IssueCostWizard(models.TransientModel):
    _name = 'issue.cost.wizard'
    period_id = fields.Many2one('finance.period', string='会计期间', help=u'根据选定期间过滤出已经生成的发出成本记录！')

    @api.multi
    def check_month_product_cost(self):
        view = self.env.ref('finance.month_product_cost_tree')
        return {
            'view_mode': 'tree',
            'views': [(view.id, 'tree')],
            'res_model': 'wh.move.line',
            'type': 'ir.actions.act_window',
            'domain': [('period_id', '=', self.period_id.id)]
        }


class MonthProductCost(models.Model):
    _name = 'month.product.cost'
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

    @api.multi
    def get_period_begin_qty_cost(self):
        pass

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
            WHERE line.type in ('in','out')
              AND line.state = 'done'
              AND line.date > '%s'
              AND line.date < '%s'
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
            res = {'current_period_in_qty': dcit_goods.get('qty'), 'current_period_in_cost': dcit_goods.get('cost')}
        else:
            res = {'current_period_out_qty': dcit_goods.get('qty'), 'current_period_out_cost': dcit_goods.get('cost')}
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
        sum_goods_cost = goods_qty_cost.get('period_begin_qty', 0) * goods_qty_cost.get('period_begin_cost', 0) - \
                         goods_qty_cost.get('current_period_out_qty', 0) * goods_qty_cost.get('current_period_out_cost',
                                                                                              0) + \
                         goods_qty_cost.get('current_period_in_qty', 0) * goods_qty_cost.get('current_period_in_cost',
                                                                                             0)
        return {'current_period_remaining_qty': sum_goods_qty,
                'current_period_remaining_cost': sum_goods_qty and sum_goods_cost * 1.0 / sum_goods_qty or 0}

    @api.multi
    def compute_balance_price(self, data_dcit):
        """
        本月该产品的结存单价 = （上月该产品的成本余额 + 本月入库成本 ）/ (上月数量余额 + 本月入库数量)
        则本月发出成本 = 结存单价 * 发出数量
        :param data_dcit:
        :return:月发出成本
        """
        balance_price = (data_dcit.get("period_begin_cost") + data_dcit.get("current_period_in_cost")) / \
                        (data_dcit.get("period_begin_qty") + data_dcit.get("current_period_in_qty"))
        return balance_price * data_dcit.get("current_period_out_qty")

    @api.multi
    def generate_issue_cost(self, period_id):
        """

        :param period_id:
        :return:
        """
        last_period = self.env['create.trial.balance.wizard'].compute_last_period_id(period_id)
        list_dict_data = self.get_stock_qty(period_id)
        month_product_cost_dict = {}
        issue_cost_exists = self.search([('period_id', '=', period_id.id)])
        issue_cost_exists.unlink()
        for dcit_goods in list_dict_data:
            vals = {}
            period_begin_qty_cost = self.get_goods_last_period_remaining_qty(period_id, dcit_goods.get('goods_id'))
            if dcit_goods.get('goods_id') not in month_product_cost_dict:
                vals = {'goods_id': dcit_goods.get('goods_id'), 'period_id': period_id.id,
                        'period_begin_qty': period_begin_qty_cost.get('current_period_remaining_qty'),
                        'period_begin_cost': period_begin_qty_cost.get('current_period_remaining_cost')}
                vals.update(self.current_period_type_current_period(dcit_goods))
                month_product_cost_dict.update({dcit_goods.get('goods_id'): vals.copy()})
                month_product_cost_dict.get(dcit_goods.get('goods_id')).update(self.month_remaining_qty_cost(
                    month_product_cost_dict.get(dcit_goods.get('goods_id'))))
            else:
                vals.update(self.current_period_type_current_period(dcit_goods))
                month_product_cost_dict.get(dcit_goods.get('goods_id')).update(vals.copy())
                month_product_cost_dict.get(dcit_goods.get('goods_id')).update(self.month_remaining_qty_cost(
                    month_product_cost_dict.get(dcit_goods.get('goods_id'))))
        voucher_line_data_list = []
        account_row = self.env.ref('finance.account_cost')
        all_balance_price = 0
        for create_vals in month_product_cost_dict.values():
            goods_row = self.env['goods'].browse(create_vals.get('goods_id'))
            voucher_line_data = {'name': u'发出成本', 'credit': self.compute_balance_price(create_vals),
                                 'account_id': goods_row.category_id.account_id.id,
                                 'goods_id': create_vals.get('goods_id')}
            voucher_line_data_list.append([0, 0, voucher_line_data.copy()])
            all_balance_price += self.compute_balance_price(create_vals)
            self.create(create_vals)
        voucher_line_data_list.append(
            [0, 0, {'name': u'发出成本', 'account_id': account_row.id, 'debit': all_balance_price}])
        voucher_id = self.env['voucher'].create({'period_id': period_id.id,'line_ids':voucher_line_data_list})
        voucher_id.voucher_done()


class CheckOutWizard(models.TransientModel):
    '''月末结账的向导'''
    _inherit = 'checkout.wizard'

    @api.multi
    def button_checkout(self):
        if self.period_id:
            self.env['month.product.cost'].generate_issue_cost(self.period_id)
        res = super(CheckOutWizard, self).button_checkout()
        return res
