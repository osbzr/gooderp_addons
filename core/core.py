# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import models, fields, api

# 单据自动编号，避免在所有单据对象上重载

create_original = models.BaseModel.create

@api.model
@api.returns('self', lambda value: value.id)
def create(self, vals):
    if not self._name.split('.')[0] == 'mail' and not vals.get('name'):
        next_name = self.env['ir.sequence'].get(self._name)
        if next_name:
            vals.update({'name': next_name})
    record_id = create_original(self, vals)
    return record_id

models.BaseModel.create = create

# 分类的类别

CORE_CATEGORY_TYPE = [('customer', u'客户'),
                      ('supplier', u'供应商'),
                      ('goods', u'商品'),
                      ('expense', u'支出'),
                      ('income', u'收入'),
                      ('other_pay', u'其他支出'),
                      ('other_get', u'其他收入'),
                      ('attribute', u'属性')]
# 成本计算方法，已实现 先入先出

CORE_COST_METHOD = [('average', u'移动平均法'),
                    ('fifo', u'先进先出法'),
                    ]


class core_value(models.Model):
    _name = 'core.value'
    name = fields.Char(u'名称')
    type = fields.Char(u'类型', default=lambda self: self._context.get('type'))


class core_category(models.Model):
    _name = 'core.category'
    name = fields.Char(u'名称')
    type = fields.Selection(CORE_CATEGORY_TYPE, u'类型',
                            default=lambda self: self._context.get('type'))


class res_company(models.Model):
    _inherit = 'res.company'
    start_date = fields.Date(
                    u'启用日期',
                    required=True,
                    default=lambda self: fields.Date.context_today(self))
    cost_method = fields.Selection(CORE_COST_METHOD, u'存货计价方法')
    draft_invoice = fields.Boolean(u'根据发票确认应收应付')


class uom(models.Model):
    _name = 'uom'
    name = fields.Char(u'名称')


class settle_mode(models.Model):
    _name = 'settle.mode'
    name = fields.Char(u'名称')


class partner(models.Model):
    _name = 'partner'
    code = fields.Char(u'编号')
    name = fields.Char(u'名称')
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    s_category_id = fields.Many2one('core.category', u'供应商类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'supplier')],
                                    context={'type': 'supplier'})
    receivable = fields.Float(u'应收余额', readonly=True,
                              digits_compute=dp.get_precision('Amount'))
    payable = fields.Float(u'应付余额', readonly=True,
                           digits_compute=dp.get_precision('Amount'))

class goods(models.Model):
    _name = 'goods'

    @api.multi
    def name_get(self):
        '''在many2one字段里显示 编号_名称'''
        res = []

        for goods in self:
            res.append((goods.id, goods.code + '_' + goods.name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''在many2one字段中支持按编号搜索'''
        args = args or []
        if name:
            goods_ids = self.search([('code', 'ilike', name)])
            if goods_ids:
                return goods_ids.name_get()
        return super(goods, self).name_search(
                name=name, args=args, operator=operator, limit=limit)

    code = fields.Char(u'编号')
    name = fields.Char(u'名称')
    category_id = fields.Many2one('core.category', u'产品类别',
                                  ondelete='restrict',
                                  domain=[('type', '=', 'goods')],
                                  context={'type': 'goods'})
    uom_id = fields.Many2one('uom', ondelete='restrict', string=u'计量单位')
    uos_id = fields.Many2one('uom', ondelete='restrict', string=u'辅助单位')
    conversion = fields.Float(u'转化率(1辅助单位等于多少计量单位)', default=1)
    cost = fields.Float(u'成本',
                        digits_compute=dp.get_precision('Amount'))
    price_ids = fields.One2many('goods.price', 'goods_id', u'价格清单')


class goods_price(models.Model):
    _name = 'goods.price'
    goods_id = fields.Many2one('goods', ondelete='cascade', string=u'商品')
    category_id = fields.Many2one('core.category', u'客户类别',
                                  ondelete='cascade',
                                  domain=[('type', '=', 'customer')],
                                  context={'type': 'customer'})
    price = fields.Float(u'价格',
                         digits_compute=dp.get_precision('Amount'))


class warehouse(models.Model):
    _name = 'warehouse'
    name = fields.Char(u'名称')


class staff(models.Model):
    _name = 'staff'
    name = fields.Char(u'名称')


class bank_account(models.Model):
    _name = 'bank.account'
    name = fields.Char(u'名称')
    balance = fields.Float(u'余额', readonly=True,
                           digits_compute=dp.get_precision('Amount'))


class res_currency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def rmb_upper(self, value):
        """
        人民币大写
        来自：http://topic.csdn.net/u/20091129/20/b778a93d-9f8f-4829-9297-d05b08a23f80.html
        传入浮点类型的值返回 unicode 字符串
        """
        rmbmap = [u"零", u"壹", u"贰", u"叁", u"肆", u"伍", u"陆", u"柒", u"捌", u"玖"]
        unit = [u"分", u"角", u"元", u"拾", u"佰", u"仟", u"万", u"拾", u"佰", u"仟", u"亿",
                u"拾", u"佰", u"仟", u"万", u"拾", u"佰", u"仟", u"兆"]

        nums = map(int, list(str('%0.2f' % value).replace('.', '')))
        words = []
        zflag = 0  # 标记连续0次数，以删除万字，或适时插入零字
        start = len(nums) - 3
        for i in range(start, -3, -1):  # 使i对应实际位数，负数为角分
            if 0 != nums[start - i] or len(words) == 0:
                if zflag:
                    words.append(rmbmap[0])
                    zflag = 0
                words.append(rmbmap[nums[start - i]])
                words.append(unit[i + 2])
            elif 0 == i or (0 == i % 4 and zflag < 3):  # 控制‘万/元’
                words.append(unit[i + 2])
                zflag = 0
            else:
                zflag += 1

        if words[-1] != unit[0]:  # 结尾非‘分’补整字
            words.append(u"整")
        return ''.join(words)
