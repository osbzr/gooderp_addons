# -*- coding: utf-8 -*-
##############################################################################
#
#    GOODERP, Open Source Management Solution
#    Copyright (C) 2018  德清武康开源软件工作室().
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

# 字段只读状态
READONLY_STATES = {
        'confirm': [('readonly', True)],
        'done': [('readonly', True)],
    }

class hr_expense(models.Model):
    '''按报销人费用汇总'''
    _name = 'hr.expense'

    name = fields.Char(u"单据编号",copy=False)
    date = fields.Date(string=u'报销日期',
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       copy=False,required=True,
                       help=u'报销发生日期')
    staff = fields.Many2one('staff', u'报销员工', required=True,help=u'选择员工')
    invoice_all_total = fields.Float(string=u'费用金额合计', store=True, readonly=True,
                                 compute='_compute_invoice_all_total', track_visibility='always',
                                 digits=dp.get_precision('Amount'))
    state = fields.Selection([('draft', u'草稿'),
                              ('confirm', u'已提交'),
                              ('done', u'已支付')], u'状态', default='draft',store=True,compute='_state_to_done')
    type = fields.Selection([
        ('company', u'付给公司'),
        ('my', u'付给报销人')], string=u'支付方式：',default='my', required=True, help=u'支付给个人时走其他付款单，支付给公司时走结算单')
    line_ids = fields.One2many('hr.expense.line', 'order_id', u'明细发票行',
                               states=READONLY_STATES, copy=False)
    note = fields.Text(u"备注")
    bank_account_id = fields.Many2one('bank.account', u'结算账户',
                                      ondelete='restrict',
                                      help=u'付给个人/公司')
    partner_id = fields.Many2one('partner', u'供应商',
                                 help=u'直接支付给供应商')

    money_invoice = fields.Many2one(
        'money.invoice', u'对应结算单', readonly=True, ondelete='restrict', copy=False)
    other_money_order = fields.Many2one(
        'other.money.order', u'对应其他应付款单', readonly=True, ondelete='restrict', copy=False)

    @api.depends('other_money_order.state')
    def _state_to_done(self):
        self.state = self.state or 'draft'
        if self.other_money_order and self.other_money_order.state == 'done':
            self.state = 'done'
        if self.other_money_order and self.other_money_order.state == 'draft':
            self.state = 'confirm'
        '''付给公司走公司对帐了，跟报销人已经没有关系，所以不DONE了吧'''

    @api.depends('line_ids')
    def _compute_invoice_all_total(self):
        total = 0
        for i in self[0].line_ids:
            total += i.invoice_total
        self[0].invoice_all_total = total

    @api.multi
    def check_consistency(self):
        category_id = []
        for line in self.line_ids:
            if line.category_id and line.category_id.id not in category_id:
                category_id.append(line.category_id.id)
            if line.staff.id != self.staff.id:
                raise UserError(u"费用明细必须是同一人！")
        if self.type == 'company':
            if len(category_id) > 1:
                raise UserError(u"申报支付给公司的费用必须同一类别！")

    @api.model
    def create(self, vals):
        res = super(hr_expense, self).create(vals)
        self.check_consistency()
        return res

    @api.multi
    def write(self, vals):
        res = super(hr_expense, self).write(vals)
        self.check_consistency()
        return res

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'只能删除草稿状态的费用报销单')
        super(hr_expense, self).unlink()

    def hr_expense_confirm(self):
        if self.state == 'confirm':
            raise UserError(u'请不要重复确认')
        if self.type == 'company':
            self.to_money_invoice()
        if self.type == 'my':
            self.to_other_money_order()
        self.state = 'confirm'

    def hr_expense_draft(self):
        '''删掉其他应付款单'''
        if self.state == 'draft':
            raise UserError(u'请不要重复撤销')
        if self.other_money_order:
            other_money_order, self.other_money_order = self.other_money_order, False
            if other_money_order.state == 'done':
                other_money_order.other_money_draft()
            other_money_order.unlink()
        '''删掉结算单'''
        if self.money_invoice:
            money_invoice, self.money_invoice = self.money_invoice, False
            if money_invoice.state == 'done':
                money_invoice.money_invoice_draft()
            money_invoice.unlink()

        self.state = 'draft'

    @api.one
    def to_money_invoice(self):
        tax = 0
        bill_number = ''
        for line in self.line_ids:
            if line.invoice_type == 'zy':
                tax += line.invoice_tax
            if line.invoice_name:
                bill_number = '%s, %s' % (line.invoice_name, bill_number)
        # todo 测试一下
        money_invoice = self.env['money.invoice'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
            'category_id': self.line_ids and self.line_ids[0].category_id.id or '',
            'date': self.date,
            'amount': self.invoice_all_total,
            'reconciled': 0,
            'to_reconcile': self.invoice_all_total,
            'date_due': fields.Date.context_today(self),
            'state': 'draft',
            'tax_amount': tax,
            'bill_number':bill_number
        })
        self.write({'money_invoice': money_invoice.id})

    @api.one
    def to_other_money_order(self):
        other_money_order = self.with_context(type='other_pay').env['other.money.order'].create({
            'state': 'draft',
            'partner_id': self.partner_id and self.partner_id.id or '',
            'date': self.date,
            'bank_id': self.bank_account_id.id,
        })
        self.write({'other_money_order': other_money_order.id})
        for line in self.line_ids:
            #增值税专用发票（ZY）税额可以抵扣！
            if line.invoice_type !='zy':
                invoice_tax = 0
                invoice_amount = line.invoice_amount +line.invoice_tax
            else:
                invoice_tax = line.invoice_tax
                invoice_amount = line.invoice_amount
            self.env['other.money.order.line'].create({
                'other_money_id': other_money_order.id,
                'amount': invoice_amount,
                'tax_rate': round(line.invoice_amount and invoice_tax / line.invoice_amount * 100,0) or 0,
                'tax_amount': invoice_tax,
                'category_id': line.category_id and line.category_id.id
            })

class hr_expense_line(models.Model):
    '''费用明细'''
    _name = 'hr.expense.line'
    _order = "date"
    name = fields.Char(u'单据编号',
                       index=True,
                       copy=False,
                       help=u"报销单的唯一编号，当创建时它会自动生成下一个编号。")
    staff = fields.Many2one('staff', required=True, string = u'报销员工', help=u'用关键字段查找并关联类别')
    invoice_type = fields.Selection([('pt', u'增值税普通发票'),
                              ('zy', u'增值税专用发票'),
                              ('dz',u'电子普通发票')], u'状态', )
    invoice_code = fields.Char(u"发票代码",copy = False)
    invoice_name = fields.Char(u"发票号码",copy = False)
    invoice_amount = fields.Float(string=u'发票金额',digits=dp.get_precision('Amount'), required=True,help=u'如是增值税发票请填不含税金额')
    invoice_tax = fields.Float(string=u'发票税额',digits=dp.get_precision('Amount'), help=u'如是增值税发票请填不含税金额')
    invoice_total = fields.Float(string=u'发票金额合计', store=True, readonly=True,
                        compute='_compute_cost_total', digits=dp.get_precision('Amount'))
    invoice_heck_code = fields.Char(u"发票校验码", copy=False)
    invoice_date = fields.Char(u"发票日期", copy=False)
    note = fields.Text(u"备注")
    state = fields.Selection([('draft', u'草稿'),
                              ('confirm', u'已提交')], u'状态',default='draft',copy = False)
    category_id = fields.Many2one('core.category',
                                  u'类别', ondelete='restrict',required=True,
                                  help=u'类型：运费、咨询费等')
    date = fields.Date(string=u'费用日期',
                       default=lambda self: fields.Date.context_today(self),
                       states={'draft': [('readonly', False)]},
                       copy=False,required=True,
                       help=u'费用发生日期')
    order_id = fields.Many2one('hr.expense', u'报销单号',  index = True, copy = False, readonly = True)
    is_refused = fields.Boolean(string="已被使用", store = True, compute='_compute_is_choose', readonly=True, copy=False)
    is_pay = fields.Boolean(string="已付款", store = True, compute='_compute_is_pay', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_invoice_code_name', 'unique (invoice_code, invoice_name)', u'发票代码+发票号码不能相同!'),
    ]
    attachment_number = fields.Integer(compute='_compute_attachment_number', string=u'附件号')

    def hr_expense_line_confirm(self):
        if self.state == 'confirm':
            raise UserError(u'请不要重复确认')
        self.state = 'confirm'

    def hr_expense_line_draft(self):
        if self.state == 'draft':
            raise UserError(u'请不要重复撤销')
        if self.state == 'confirm' and not self.is_refused:
            self.state = 'draft'
        else:
            raise UserError(u"请先解除关联单据%s"%self.order_id.name)


    @api.depends('invoice_amount', 'invoice_tax')
    def _compute_cost_total(self):
        for expense_line in self:
            expense_line.invoice_total = expense_line.invoice_amount + expense_line.invoice_tax

    @api.depends('order_id')
    def _compute_is_choose(self):
        for expense_line in self:
            if expense_line.order_id:
                expense_line.is_refused = True
            else:
                expense_line.is_refused = False

    @api.model
    def saomiaofapiao(self, model_name, barcode, order_id):
        """
        扫描发票条码
        :param model_name: 模型名
        :param barcode: 二维码识别内容
        :return:

        01,10,033001600211,11255692,349997.85,20180227,62521957050111533932,7DF9,
        01：第一个属性值，尚未搞清楚含义；
        10：第二个属性值，代表发票种类代码，10-电子普通发票，04-增值税普通发票，01-增值税专用发票；
        033001600211：第三个属性值，代表发票代码；
        11255692：第四个属性值，代表发票号码；
        349997.85：第五个属性值，代表开票金额（不含税）；
        20180227：第六个属性值，代表开票日期，该值为2016年10月18日；
        62521957050111533932：第七个属性值，代码发票校验码，我们都知道增值税专用发票是没有发票校验码的，没有则为空字符串；

        """
        #中文模式下替換字符
        barcode = barcode.replace(u'，', ',')
        barcode = barcode.replace(u'。', '.')
        code = barcode.split(',')
        invoice_heck_code = ''
        if len(code) < 5:
            raise UserError(u"请确认扫描是否正确%s" % code)
        if code[0] == '01':
            if code[1] == '10':
                invoice_type = 'dz'
                invoice_heck_code = code[6]
            if code[1] == '01':
                invoice_type = 'zy'
            if code[1] == '04':
                invoice_type = 'pt'
                invoice_heck_code = code[6]
            invoice_code = code[2]
            invoice_name = code[3]
            invoice_amount = round(float(code[4]),2)
            invoice_date = code[5]
            invoice_tax = 0
        self.browse(order_id).write({
            'invoice_type': invoice_type,
            'invoice_code': invoice_code,
            'invoice_name': invoice_name,
            'invoice_amount': invoice_amount,
            'invoice_tax': invoice_tax,
            'invoice_heck_code': invoice_heck_code,
            'invoice_date': invoice_date
        })

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense.line'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense.line', 'default_res_id': self.id}
        return res

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'hr.expense.line'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'只能删除草稿状态的费用发票')
        super(hr_expense_line, self).unlink()

    @api.one
    @api.depends('order_id.state')
    def _compute_is_pay(self):
        if self.order_id and self.order_id.state == 'done':
            self.is_pay = True
        else:
            self.is_pay = False
