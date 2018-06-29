# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero


class MonthProductCost(models.Model):
    _name = 'month.product.cost'
    _description = u'每月发出成本'

    period_id = fields.Many2one('finance.period', string='会计期间')
    goods_id = fields.Many2one('goods', string="商品")
    period_begin_qty = fields.Float(
        string='期初数量', digits=dp.get_precision('Quantity'))
    period_begin_cost = fields.Float(
        string='期初成本', digits=dp.get_precision('Amount'),)
    current_period_out_qty = fields.Float(
        string='本期出库量', digits=dp.get_precision('Quantity'))
    current_period_out_cost = fields.Float(
        string='本期出库成本', digits=dp.get_precision('Amount'),)
    current_period_in_qty = fields.Float(
        string='本期入库量', digits=dp.get_precision('Quantity'))
    current_period_in_cost = fields.Float(
        string='本期入库成本', digits=dp.get_precision('Amount'),)
    current_period_remaining_qty = fields.Float(
        string='本期剩余数量', digits=dp.get_precision('Quantity'))
    current_period_remaining_cost = fields.Float(
        string='剩余数量成本', digits=dp.get_precision('Amount'),)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.multi
    def get_stock_qty(self, period_id):
        date_range = self.env['finance.period'].get_period_month_date_range(
            period_id)
        # 每个产品最多取两行，一个本月出库，一个本月入库
        # 如果一个产品在本月没有出入库记录，则不生成发出成本记录
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
        last_period_remaining_qty = 0
        last_period_remaining_cost = 0

        # 查找 离输入期间最近的 对应产品的发出成本行
        last_month_product_cost_row = self.search([('period_id.id', '<', period_id.id),
                                                   ('goods_id', '=', goods_id)], limit=1, order='id desc')
        if last_month_product_cost_row:
            last_period_remaining_qty = last_month_product_cost_row.current_period_remaining_qty
            last_period_remaining_cost = last_month_product_cost_row.current_period_remaining_cost

        return {
            'last_period_remaining_qty': last_period_remaining_qty,
            'last_period_remaining_cost': last_period_remaining_cost
        }

    @api.multi
    def fill_in_out(self, dcit_goods):
        """
      填充产品的本月出库入库数量和成本
      这里填充的是实际出库成本，后面会调整成按 公司成本核算方式 计算的成本
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
        算出 本月的剩余的数量和成本
        """
        sum_goods_qty = goods_qty_cost.get('period_begin_qty', 0) - \
            goods_qty_cost.get('current_period_out_qty', 0) + \
            goods_qty_cost.get('current_period_in_qty', 0)
        sum_goods_cost = goods_qty_cost.get('period_begin_cost', 0) - \
            goods_qty_cost.get('current_period_out_cost', 0) + \
            goods_qty_cost.get('current_period_in_cost', 0)
        return {'current_period_remaining_qty': sum_goods_qty,
                'current_period_remaining_cost': sum_goods_cost
                }

    def _get_cost_method(self, goods_id):
        '''
        批次管理的产品使用个别计价
        先取产品的计价方式，再取公司上的计价方式
        '''
        goods = self.env.get('goods').browse(goods_id)
        if goods.using_batch:
            return 'fifo'
        if goods.cost_method:
            return goods.cost_method
        else:
            return self.env.user.company_id.cost_method

    @api.multi
    def compute_balance_price(self, data_dict):
        """
可以用其他算法计算发出成本
        """
        cost_method = self._get_cost_method(data_dict.get("goods_id"))
        if cost_method == 'average':
            # 本月该商品的结存单价 = （上月该商品的成本余额 + 本月入库成本 ）/ (上月数量余额 + 本月入库数量)
            # 则本月发出成本 = 结存单价 * 发出数量
            balance_price = (data_dict.get("period_begin_cost", 0) + data_dict.get("current_period_in_cost", 0)) / \
                            ((data_dict.get("period_begin_qty", 0) +
                              data_dict.get("current_period_in_qty", 0)) or 1)
            month_cost = balance_price * \
                data_dict.get("current_period_out_qty", 0)
        if cost_method == 'fifo':
            # 实际成本
            month_cost = data_dict.get("current_period_out_cost", 0)
        if cost_method == 'std':
            # 定额成本
            goods = self.env.get('goods').browse(data_dict.get("goods_id"))
            month_cost =  goods.price * \
                data_dict.get("current_period_out_qty", 0)
        return round(month_cost, 2)

    @api.multi
    def compute_real_out_cost(self, data_dict, period_id):
        """
        计算当期库存商品科目（所有商品类别涉及的科目）贷方金额合计
        """
        line = self.env['voucher.line'].search([
            ('goods_id', '=', data_dict.get('goods_id')),
            ('voucher_id.period_id', '=', period_id.id),
            ('credit', '>', 0)
        ])
        cost = sum(l.credit for l in line)
        return cost

    @api.multi
    def create_month_product_cost_voucher(self, period_id, date, month_product_cost_dict):
        """
        月底成本结转生成的凭证，算出借贷方金额后，借贷方金额全部减去本期间库存商品科目（所有商品类别涉及的科目）贷方金额合计
        :param period_id:
        :param date:
        :param month_product_cost_dict:
        :return:
        """

        voucher_line_data_list = []
        account_row = self.env.ref('finance.account_cost')
        all_balance_price = 0
        for create_vals in month_product_cost_dict.values():
            goods_row = self.env['goods'].browse(create_vals.get('goods_id'))
            current_period_out_cost = self.compute_balance_price(
                create_vals)   # 当期加权平均成本
            real_out_cost = self.compute_real_out_cost(
                create_vals, period_id)  # 发出时已结转的实际成本

            diff_cost = current_period_out_cost - real_out_cost  # 两者之差
            if not float_is_zero(diff_cost,2):  # 贷方
                voucher_line_data = {'name': u'发出成本', 'credit': diff_cost,
                                     'account_id': goods_row.category_id.account_id.id,
                                     'goods_id': create_vals.get('goods_id'),
                                     'goods_qty': create_vals.get('current_period_out_qty')}
                voucher_line_data_list.append([0, 0, voucher_line_data.copy()])
                all_balance_price += diff_cost
            # 创建 发出成本
            create_vals.update({'current_period_out_cost': current_period_out_cost,
                                'current_period_remaining_cost': create_vals.get('period_begin_cost', 0) +
                                create_vals.get('current_period_in_cost', 0) -
                                current_period_out_cost
                                })
            self.create(create_vals)

        if all_balance_price != 0:  # 借方
            voucher_line_data_list.append(
                [0, 0, {'name': u'发出成本', 'account_id': account_row.id, 'debit': all_balance_price}])
        if voucher_line_data_list:
            voucher_id = self.env['voucher'].create({'date': date, 'period_id': period_id.id,
                                                     'line_ids': voucher_line_data_list,
                                                     'is_checkout': True})
            voucher_id.voucher_done()

    @api.multi
    def data_structure(self, list_dict_data, period_id):
        """
        把 list_dict_data 按产品合并成 month_product_cost_dict，并填充期初、期末
        """
        month_product_cost_dict = {}
        for dict_goods in list_dict_data:
            period_begin_qty_cost = self.get_goods_last_period_remaining_qty(
                period_id, dict_goods.get('goods_id'))
            vals = {}
            if dict_goods.get('goods_id') not in month_product_cost_dict:
                vals = {'goods_id': dict_goods.get('goods_id'), 'period_id': period_id.id,
                        'period_begin_qty': period_begin_qty_cost.get('last_period_remaining_qty', 0),
                        'period_begin_cost': period_begin_qty_cost.get('last_period_remaining_cost', 0)}
                vals.update(self.fill_in_out(dict_goods))
                month_product_cost_dict.update(
                    {dict_goods.get('goods_id'): vals.copy()})
                month_product_cost_dict.get(dict_goods.get('goods_id')).update(self.month_remaining_qty_cost(
                    month_product_cost_dict.get(dict_goods.get('goods_id'))))
            else:
                vals.update(self.fill_in_out(dict_goods))
                month_product_cost_dict.get(
                    dict_goods.get('goods_id')).update(vals.copy())
                month_product_cost_dict.get(dict_goods.get('goods_id')).update(self.month_remaining_qty_cost(
                    month_product_cost_dict.get(dict_goods.get('goods_id'))))

        return month_product_cost_dict

    @api.multi
    def generate_issue_cost(self, period_id, date):
        """
        生成成本的凭证
        :param period_id:
        :return:
        """
        list_dict_data = self.get_stock_qty(period_id)
        issue_cost_exists = self.search([('period_id', '=', period_id.id)])
        issue_cost_exists.unlink()
        self.create_month_product_cost_voucher(
            period_id, date, self.data_structure(list_dict_data, period_id))


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
                self.env['month.product.cost'].generate_issue_cost(
                    self.period_id, self.date)
        res = super(CheckOutWizard, self).button_checkout()
        return res

    # 反结账
    @api.multi
    def button_counter_checkout(self):
        ''' 反结账 删除对应出库成本 '''
        if self.period_id:
            issue_cost_exists = self.env['month.product.cost'].search(
                [('period_id', '=', self.period_id.id)])
            issue_cost_exists.unlink()

        res = super(CheckOutWizard, self).button_counter_checkout()
        return res
