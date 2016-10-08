# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api
from odoo.exceptions import UserError

# 单据自动编号，避免在所有单据对象上重载

create_original = models.BaseModel.create

@api.model
@api.returns('self', lambda value: value.id)
def create(self, vals):
    if not self._name.split('.')[0] in ['mail','ir','res'] and not vals.get('name'):
        next_name = self.env['ir.sequence'].next_by_code(self._name)
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
    name = fields.Char(u'名称', required=True)
    type = fields.Char(u'类型', required=True, default=lambda self: self._context.get('type'))
    note = fields.Text(u'备注')
    _sql_constraints = [
        ('name_uniq', 'unique (name)', '可选值不能重名')
    ]


class core_category(models.Model):
    _name = 'core.category'
    name = fields.Char(u'名称', required=True)
    type = fields.Selection(CORE_CATEGORY_TYPE, u'类型',
                            required=True,
                            default=lambda self: self._context.get('type'))
    note = fields.Text(u'备注')
    _sql_constraints = [
        ('name_uniq', 'unique (name)', '类别不能重名')
    ]


class res_company(models.Model):
    _inherit = 'res.company'
    start_date = fields.Date(
                    u'启用日期',
                    required=True,
                    default=lambda self: fields.Date.context_today(self))
    cost_method = fields.Selection(CORE_COST_METHOD, u'存货计价方法')
    draft_invoice = fields.Boolean(u'根据发票确认应收应付')
    import_tax_rate=fields.Float(string=u"默认进项税税率")
    output_tax_rate=fields.Float(string=u"默认销项税税率")


class uom(models.Model):
    _name = 'uom'
    name = fields.Char(u'名称', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '单位不能重名')
    ]

class settle_mode(models.Model):
    _name = 'settle.mode'
    name = fields.Char(u'名称', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '结算方式不能重名')
    ]

class partner(models.Model):
    _name = 'partner'
    code = fields.Char(u'编号')
    name = fields.Char(u'名称',required=True,)
    main_mobile = fields.Char(u'主要手机号',required=True,)
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    s_category_id = fields.Many2one('core.category', u'供应商类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'supplier')],
                                    context={'type': 'supplier'})
    receivable = fields.Float(u'应收余额', readonly=True,
                              digits=dp.get_precision('Amount'))
    payable = fields.Float(u'应付余额', readonly=True,
                           digits=dp.get_precision('Amount'))
    tax_num = fields.Char(u'税务登记号')
    bank_name = fields.Char(u'开户行')
    bank_num = fields.Char(u'银行账号')

    credit_limit = fields.Float(u'信用额度',
                                help=u'客户购买产品时，本次发货金额+客户应收余额要小于客户信用额度')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '业务伙伴不能重名')
    ]

class goods(models.Model):
    _name = 'goods'

    @api.multi
    def name_get(self):
        '''在many2one字段里显示 编号_名称'''
        res = []

        for goods in self:
            res.append((goods.id, goods.code and (goods.code + '_' + goods.name) or goods.name))
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

    @api.model
    def create(self, vals):
        '''导入产品时，如果辅助单位为空，则用计量单位来填充它'''
        if not vals.get('uos_id'):
            vals.update({'uos_id': vals.get('uom_id')})
        return super(goods, self).create(vals)

    code = fields.Char(u'编号')
    name = fields.Char(u'名称', required=True)
    category_id = fields.Many2one('core.category', u'产品类别',
                                  ondelete='restrict',
                                  domain=[('type', '=', 'goods')],
                                  context={'type': 'goods'}, required=True)
    uom_id = fields.Many2one('uom', ondelete='restrict', string=u'计量单位', required=True)
    uos_id = fields.Many2one('uom', ondelete='restrict', string=u'辅助单位')
    conversion = fields.Float(u'转化率(1辅助单位等于多少计量单位)', default=1, help=u'转化率就是计量单位和辅助单位的互换的比例！')
    cost = fields.Float(u'成本',
                        required=True,
                        digits=dp.get_precision('Amount'))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '产品不能重名')
    ]

class warehouse(models.Model):
    _name = 'warehouse'

    WAREHOUSE_TYPE = [
        ('stock', u'库存'),
        ('supplier', u'供应商'),
        ('customer', u'客户'),
        ('inventory', u'盘点'),
        ('production', u'生产'),
        ('others', u'其他'),
    ]

    name = fields.Char(u'名称', required=True)
    code = fields.Char(u'编号')
    type = fields.Selection(WAREHOUSE_TYPE, u'类型', default='stock')
    active = fields.Boolean(u'有效', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '仓库不能重名')
    ]

    def get_stock_qty(self):
        '''使用SQL来取得指定仓库的库存数量'''
        for warehouse in self:
            self.env.cr.execute('''
                SELECT sum(line.qty_remaining) as qty,
                       sum(line.qty_remaining * (line.cost / line.goods_qty)) as cost,
                       goods.name as goods
                FROM wh_move_line line
                LEFT JOIN warehouse wh ON line.warehouse_dest_id = wh.id
                LEFT JOIN goods goods ON line.goods_id = goods.id

                WHERE line.qty_remaining > 0
                  AND wh.type = 'stock'
                  AND line.state = 'done'
                  AND line.warehouse_dest_id = %s

                GROUP BY wh.name, goods.name
            ''' % (warehouse.id, ))

            return self.env.cr.dictfetchall()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ''' 让warehouse支持使用code来搜索'''
        args = args or []
        # 将name当成code搜
        if name and not filter(lambda _type: _type[0] == 'code', args):
            warehouses = self.search([('type', '=', 'stock'), ('code', 'ilike', name)])
            if warehouses:
                return warehouses.name_get()
        # 下拉列表只显示库存类型的仓库
        if not filter(lambda _type: _type[0] == 'type', args):
            args = [['type', '=', 'stock']] + args

        return super(warehouse, self).name_search(name=name, args=args,
            operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        '''将仓库显示为 [编号]名字 的形式'''
        res = []
        for warehouse in self:
            res.append((warehouse.id, u'[%s]%s' % (warehouse.code, warehouse.name)))

        return res

    def get_warehouse_by_type(self, _type):
        '''返回指定类型的第一个仓库'''
        if not _type or _type not in map(lambda _type: _type[0], self.WAREHOUSE_TYPE):
            raise UserError(u'仓库类型" % s"不在预先定义的type之中，请联系管理员' % _type)

        warehouses = self.search([('type', '=', _type)], limit=1, order='id asc')
        if not warehouses:
            raise UserError(u'不存在该类型" % s"的仓库，请检查基础数据是否全部导入')

        return warehouses[0]

class staff(models.Model):
    _name = 'staff'
    name = fields.Char(u'名称', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '员工不能重名')
    ]

class bank_account(models.Model):
    _name = 'bank.account'
    name = fields.Char(u'名称', required=True)
    balance = fields.Float(u'余额', readonly=True,
                           digits=dp.get_precision('Amount'))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '账户不能重名')
    ]

class pricing(models.Model):
    _name = 'pricing'
    _description = u'定价策略'

    @api.model
    def get_pricing_id(self, partner, warehouse, goods, date):
        '''传入客户，仓库，商品，日期，返回合适的价格策略，如果找到两条以上符合的规则，则报错
        1. 客户类别、仓库、商品
        2. 客户类别、仓库、商品类别
        3. 客户类别、仓库
        4. 仓库、商品
        5. 仓库，商品分类
        6. 仓库
        7. 客户类别、商品
        8. 客户类别、商品分类
        9. 客户类别
        10. 所有商品
        11. 可能还是找不到有效期内的，返回 False
        '''
        if not partner:
            raise UserError(u'请先输入客户')
        if not warehouse:
            raise UserError(u'请先输入仓库')
        if not goods:
            raise UserError(u'请先输入商品')
        # 客户类别、仓库、产品满足条件
        good_pricing = self.search([
                                    ('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', goods.id),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)
                                    ])
        # 客户类别、仓库、产品
        if len(good_pricing) == 1:
            return good_pricing
        if len(good_pricing) > 1:
            raise UserError(u'适用于%s,%s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                                  warehouse.name,
                                                                  goods.name,
                                                                  date))
        # 客户类别、仓库、产品类别满足条件
        gc_pricing = self.search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',goods.category_id.id),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        # 客户类别、仓库、产品类别
        if len(gc_pricing) == 1:
            return gc_pricing
        if len(gc_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                                  warehouse.name,
                                                                  goods.category_id.name,
                                                                  date))
        # 客户类别、仓库满足条件
        pw_pricing = self.search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',False),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        # 客户类别、仓库
        if len(pw_pricing) == 1:
            return pw_pricing
        if len(pw_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                                warehouse.name,
                                                                date))
        # 仓库、商品满足
        wg_pricing = self.search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 仓库、商品
        if len(wg_pricing) == 1:
            return wg_pricing
        if len(wg_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (warehouse.name,
                                                                goods.name,
                                                                date))
        # 仓库，商品分类满足条件
        w_gc_pricing = self.search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 仓库，商品分类
        if len(w_gc_pricing) == 1:
            return w_gc_pricing
        if len(w_gc_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (warehouse.name,
                                                                goods.category_id.name,
                                                                date))
        # 仓库满足条件
        warehouse_pricing = self.search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 仓库
        if len(warehouse_pricing) == 1:
            return warehouse_pricing
        if len(warehouse_pricing) > 1:
            raise UserError(u'适用于 %s,%s 的价格策略不唯一' % (warehouse.name,
                                                             date))
        # 客户类别,商品满足条件
        ccg_pricing = self.search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 客户类别,商品
        if len(ccg_pricing) == 1:
            return ccg_pricing
        if len(ccg_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                                goods.name,
                                                                date))
        # 客户类别,产品分类满足条件
        ccgc_pricing = self.search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 客户类别，产品分类
        if len(ccgc_pricing) == 1:
            return ccgc_pricing
        if len(ccgc_pricing) > 1:
            raise UserError(u'适用于 %s,%s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                                goods.category_id.name,
                                                                date))
        # 客户类别满足条件
        partner_pricing = self.search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 客户类别
        if len(partner_pricing) == 1:
            return partner_pricing
        if len(partner_pricing) > 1:
            raise UserError(u'适用于 %s,%s 的价格策略不唯一' % (partner.c_category_id.name,
                                                             date))
        # 所有产品打折
        all_goods_pricing = self.search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        # 所有产品
        if len(all_goods_pricing) == 1:
            return all_goods_pricing
        if len(all_goods_pricing) > 1:
            raise UserError(u'适用于 %s 的价格策略不唯一' % (date))
        # 如果日期范围内没有适用的价格策略，则返回空
        if len(good_pricing)+len(gc_pricing)+len(pw_pricing)+len(wg_pricing)\
                +len(w_gc_pricing)+len(warehouse_pricing)+len(ccg_pricing)\
                +len(partner_pricing)+len(all_goods_pricing) == 0:
            return False
            

    name=fields.Char(u'描述', help=u'描述!')
    warehouse_id = fields.Many2one('warehouse',u'仓库')
    c_category_id = fields.Many2one('core.category', u'客户类别',
                                    ondelete='restrict',
                                    domain=[('type', '=', 'customer')],
                                    context={'type': 'customer'})
    goods_category_id = fields.Many2one('core.category', u'产品类别',
                                  ondelete='restrict',
                                  domain=[('type', '=', 'goods')],
                                  context={'type': 'goods'})
    goods_id = fields.Many2one('goods',u'产品')
    active_date = fields.Date(u'开始日期', required=True)
    deactive_date = fields.Date(u'终止日期', required=True)
    discount_rate = fields.Float(u'折扣率%', help=u'产品的价格 × 折扣率 = 产品的实际价格 !')


class res_currency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def rmb_upper(self, value):
        """
        人民币大写
        来自：http://topic.csdn.net/u/20091129/20/b778a93d-9f8f-4829-9297-d05b08a23f80.html
        传入浮点类型的值返回 unicode 字符串
        :param 传入阿拉伯数字
        :return 返回值是对应阿拉伯数字的绝对值的中文数字
        """
        rmbmap = [u"零", u"壹", u"贰", u"叁", u"肆", u"伍", u"陆", u"柒", u"捌", u"玖"]
        unit = [u"分", u"角", u"元", u"拾", u"佰", u"仟", u"万", u"拾", u"佰", u"仟", u"亿",
                u"拾", u"佰", u"仟", u"万", u"拾", u"佰", u"仟", u"兆"]
        # 冲红负数处理
        xflag = 0
        if value < 0:
            xflag = value
            value = abs(value)
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
        if xflag < 0:
            words.insert(0, u"负")
        return ''.join(words)


class service(models.Model):
    _name = 'service'
    _description = u'服务'

    name = fields.Char(u'名称', required=True)
    get_categ_id = fields.Many2one('core.category',
                    u'收入类别', ondelete='restrict',
                    domain="[('type', '=', 'other_get')]")
    pay_categ_id = fields.Many2one('core.category',
                    u'支出类别', ondelete='restrict',
                    domain="[('type', '=', 'other_pay')]")
    price = fields.Float(u'价格', required=True)


class res_users(models.Model):
    _inherit = 'res.users'

    @api.multi
    def write(self, vals):
        res = super(res_users, self).write(vals)
        # 如果普通用户修改管理员，则报错
        if self.env.user.id != 1:
            for record in self:
                if record.id == 1:
                    raise UserError(u'系统用户不可修改')
        # 如果管理员将自己的系统管理权限去掉，则报错
        else:
            if not self.env.user.has_group('base.group_erp_manager'):
                raise UserError(u'不能删除管理员的管理权限')
        return res
