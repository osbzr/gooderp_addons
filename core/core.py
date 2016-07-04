# -*- coding: utf-8 -*-

import openerp.addons.decimal_precision as dp
from openerp import models, fields, api
from openerp.exceptions import except_orm

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
    name = fields.Char(u'名称')


class settle_mode(models.Model):
    _name = 'settle.mode'
    name = fields.Char(u'名称')


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


class pricing(models.Model):
    _name = 'pricing'

    @api.model
    def get_pricing_id(self,partner,warehouse,goods,date):
        '''传入客户，仓库，商品，日期，返回合适的价格策略'''
        if not partner:
            raise except_orm(u'错误',u'请先输入客户')
        if not warehouse:
            raise except_orm(u'错误',u'请先输入仓库')
        if partner and warehouse and goods:
            #客户类别、仓库、产品满足条件
            good_pricing = self.search([
                                        ('c_category_id','=',partner.c_category_id.id),
                                        ('warehouse_id','=',warehouse.id),
                                        ('goods_id','=',goods.id),
                                        ('goods_category_id','=',False),
                                        ('active_date','<=',date),
                                        ('deactive_date','>=',date)
                                        ])
            #仓库，客户类别，产品
            if len(good_pricing) == 1 :
                return good_pricing
            if len(good_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s,%s 的价格策略不唯一'%(partner.c_category_id.name,
                                                                 warehouse.name,
                                                                 goods.name,
                                                                 date))
            #客户类别、仓库、产品类别满足条件
            gc_pricing = self.search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
            #仓库，客户类别，产品分类
            if len(gc_pricing) == 1 :
                return gc_pricing
            if len(gc_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s,%s 的价格策略不唯一'%(partner.c_category_id.name,
                                                                 warehouse.name,
                                                                 goods.category_id.name,
                                                                 date))
            #客户类别、仓库满足条件
            pw_pricing = self.search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
            #仓库，客户类别
            if len(pw_pricing) == 1 :
                return pw_pricing
            if len(pw_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s 的价格策略不唯一'%(partner.c_category_id.name,
                                                                 warehouse.name,
                                                                 date))
            #仓库,产品满足
            wg_pricing = self.search([
                                          ('c_category_id','=',False),
                                          ('warehouse_id','=',warehouse.id),
                                          ('goods_id','=',goods.id),
                                          ('goods_category_id','=',False),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #仓库，产品
            if len(wg_pricing) == 1 :
                return wg_pricing
            if len(wg_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s 的价格策略不唯一'%(warehouse.name,
                                                                 goods.name,
                                                                 date))
            #仓库，产品分类满足条件
            w_gc_pricing = self.search([
                                          ('c_category_id','=',False),
                                          ('warehouse_id','=',warehouse.id),
                                          ('goods_id','=',False),
                                          ('goods_category_id','=',goods.category_id.id),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #仓库，产品分类
            if len(w_gc_pricing) == 1 :
                return w_gc_pricing
            if len(w_gc_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s 的价格策略不唯一'%(warehouse.name,
                                                                 goods.category_id.name,
                                                                 date))
            #仓库满足条件
            warehouse_pricing = self.search([
                                          ('c_category_id','=',False),
                                          ('warehouse_id','=',warehouse.id),
                                          ('goods_id','=',False),
                                          ('goods_category_id','=',False),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #仓库
            if len(warehouse_pricing) == 1 :
                return warehouse_pricing
            if len(warehouse_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s 的价格策略不唯一'%(warehouse.name,
                                                                 date))
            #客户类别,产品满足条件
            ccg_pricing = self.search([
                                          ('c_category_id','=',partner.c_category_id.id),
                                          ('warehouse_id','=',False),
                                          ('goods_id','=',goods.id),
                                          ('goods_category_id','=',False),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #客户类别，产品
            if len(ccg_pricing) == 1 :
                return ccg_pricing
            if len(ccg_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s 的价格策略不唯一'%(partner.c_category_id.name,
                                                                 goods.name,
                                                                 date))
            #客户类别,产品分类满足条件
            ccgc_pricing = self.search([
                                          ('c_category_id','=',partner.c_category_id.id),
                                          ('warehouse_id','=',False),
                                          ('goods_id','=',False),
                                          ('goods_category_id','=',goods.category_id.id),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #仓库，产品分类
            if len(ccgc_pricing) == 1 :
                return ccgc_pricing
            if len(ccgc_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s,%s 的价格策略不唯一'%(partner.c_category_id.name,
                                                                 goods.category_id.name,
                                                                 date))
            #客户类别满足条件
            partner_pricing = self.search([
                                          ('c_category_id','=',partner.c_category_id.id),
                                          ('warehouse_id','=',False),
                                          ('goods_id','=',False),
                                          ('goods_category_id','=',False),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #客户类别
            if len(partner_pricing) == 1 :
                return partner_pricing
            if len(partner_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s,%s 的价格策略不唯一'%(partner.c_category_id.name,
                                                                 date))
            #所有产品打折
            all_goods_pricing = self.search([
                                          ('c_category_id','=',False),
                                          ('warehouse_id','=',False),
                                          ('goods_id','=',False),
                                          ('goods_category_id','=',False),
                                          ('active_date','<=',date),
                                          ('deactive_date','>=',date)
                                          ])
            #所有产品
            if len(all_goods_pricing) == 1 :
                return all_goods_pricing
            if len(all_goods_pricing) > 1 :
                raise except_orm(u'错误', 
                                 u'适用于 %s 的价格策略不唯一'%(date))
            if len(good_pricing)+len(gc_pricing)+len(pw_pricing)+len(wg_pricing)\
                    +len(w_gc_pricing)+len(warehouse_pricing)+len(ccg_pricing)\
                    +len(partner_pricing)+len(all_goods_pricing) == 0:
                return False
            

    name=fields.Char(u'描述')
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
    active_date = fields.Date(u'开始日期')
    deactive_date = fields.Date(u'终止日期')
    discount_rate = fields.Float(u'折扣率%')
    
    


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

    name = fields.Char(u'名称')
    get_categ_id = fields.Many2one('core.category',
                    u'收入类别', ondelete='restrict',
                    domain="[('type', '=', 'other_get')]")
    pay_categ_id = fields.Many2one('core.category',
                    u'支出类别', ondelete='restrict',
                    domain="[('type', '=', 'other_pay')]")
    price = fields.Float(u'价格')
