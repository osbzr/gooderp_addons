# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import fields, models, api, tools

from odoo.addons.report_docx.report.report_docx import ReportDocx, DataModelProxy
from odoo.addons.report_docx.report import report_helper
from docxtpl import DocxTemplate
from odoo.tools import misc
import tempfile
import os


class SupplierStatementsReport(models.Model):
    _name = "supplier.statements.report"
    _description = u"供应商对账单"
    _auto = False
    _order = 'id, date'

    @api.one
    @api.depends('amount', 'pay_amount', 'partner_id')
    def _compute_balance_amount(self):
        # 相邻的两条记录，partner不同，应付款余额要清零并重新计算
        pre_record = self.search(
            [('id', '<=', self.id), ('partner_id', '=', self.partner_id.id)])
        for pre in pre_record:
            self.balance_amount += pre.amount - pre.pay_amount + pre.discount_money

    partner_id = fields.Many2one('partner', string=u'业务伙伴', readonly=True)
    name = fields.Char(string=u'单据编号', readonly=True)
    date = fields.Date(string=u'单据日期', readonly=True)
    done_date = fields.Datetime(string=u'完成日期', readonly=True)
    amount = fields.Float(string=u'应付金额', readonly=True,
                          digits=dp.get_precision('Amount'))
    pay_amount = fields.Float(string=u'实际付款金额', readonly=True,
                              digits=dp.get_precision('Amount'))
    discount_money = fields.Float(string=u'付款折扣', readonly=True,
                                  digits=dp.get_precision('Amount'))
    balance_amount = fields.Float(
        string=u'应付款余额',
        compute='_compute_balance_amount',
        readonly=True,
        digits=dp.get_precision('Amount'))
    note = fields.Char(string=u'备注', readonly=True)

    def init(self):
        # union money_order(type = 'pay'), money_invoice(type = 'expense')
        cr = self._cr
        tools.drop_view_if_exists(cr, 'supplier_statements_report')
        cr.execute("""
            CREATE or REPLACE VIEW supplier_statements_report AS (
            SELECT  ROW_NUMBER() OVER(ORDER BY partner_id, date, amount desc) AS id,
                    partner_id,
                    name,
                    date,
                    done_date,
                    amount,
                    pay_amount,
                    discount_money,
                    balance_amount,
                    note
            FROM
                (
                SELECT m.partner_id,
                        m.name,
                        m.date,
                        m.write_date AS done_date,
                        0 AS amount,
                        m.amount AS pay_amount,
                        m.discount_amount AS discount_money,
                        0 AS balance_amount,
                        m.note
                FROM money_order AS m
                WHERE m.type = 'pay' AND m.state = 'done'
                UNION ALL
                SELECT  mi.partner_id,
                        mi.name,
                        mi.date,
                        mi.create_date AS done_date,
                        mi.amount,
                        0 AS pay_amount,
                        0 AS discount_money,
                        0 AS balance_amount,
                        Null AS note
                FROM money_invoice AS mi
                LEFT JOIN core_category AS c ON mi.category_id = c.id
                WHERE c.type = 'expense' AND mi.state = 'done'
                ) AS ps)
        """)


class IrActionReportDocx(models.Model):
    _inherit = 'ir.actions.report.xml'

    def _lookup_report(self, name):
        self._cr.execute(
            "SELECT * FROM ir_act_report_xml WHERE report_name=%s", (name,))
        r = self._cr.dictfetchone()
        if r:
            if r['model'] == 'partner.statements.report.wizard' and r['report_type'] == 'docx':
                return ReportDocxPartner('report.' + r['report_name'], r['model'], register=False)

        return super(IrActionReportDocx, self)._lookup_report(name)


class ReportDocxPartner(ReportDocx):
    def create(self, cr, uid, ids, data, context=None):
        env = api.Environment(cr, uid, context)
        report_ids = env.get('ir.actions.report.xml').search([('report_name', '=', self.name[7:])])
        self.title = report_ids[0].name
        if report_ids[0].report_name == 'supplier.statements.report':
            return self.supplier_statement_report(cr, uid, ids, report_ids[0], context=context)
        elif report_ids[0].report_name == 'customer.statements.report':
            return self.customer_statement_report(cr, uid, ids, report_ids[0], context=context)

        return super(ReportDocxPartner, self).create(cr, uid, ids, data, context)

    def supplier_statement_report(self, cr, uid, ids, report_id, context=None):
        env = api.Environment(cr, uid, context)
        records = env.get('supplier.statements.report').search([('partner_id', '=', context.get('partner_id')),
                                                                ('date', '>=', context.get('from_date')),
                                                                ('date', '<=', context.get('to_date'))])
        if records:
            return self.create_source_docx_partner(cr, uid, ids, report_id, records, 0, context)
        else:
            pre_records = env.get('supplier.statements.report').search(
                [('partner_id', '=', context.get('partner_id')),
                 ('date', '<', context.get('from_date'))], order='id desc')
            if pre_records:
                init_pay = pre_records[0].balance_amount
                return self.create_source_docx_partner(cr, uid, ids, report_id, None, init_pay, context)
            else:
                return self.create_source_docx_partner(cr, uid, ids, report_id, None, 0, context)

    def customer_statement_report(self, cr, uid, ids, report_id, context=None):
        env = api.Environment(cr, uid, context)
        records = env.get('customer.statements.report').search([('partner_id', '=', context.get('partner_id')),
                                                                ('date', '>=', context.get('from_date')),
                                                                ('date', '<=', context.get('to_date'))])
        if records:
            return self.create_source_docx_partner(cr, uid, ids, report_id, records, 0, context)
        else:
            pre_records = env.get('customer.statements.report').search(
                [('partner_id', '=', context.get('partner_id')),
                 ('date', '<', context.get('from_date'))], order='id desc')
            if pre_records:
                init_pay = pre_records[0].balance_amount
                return self.create_source_docx_partner(cr, uid, ids, report_id, None, init_pay, context)
            else:
                return self.create_source_docx_partner(cr, uid, ids, report_id, None, 0, context)

    def create_source_docx_partner(self, cr, uid, ids, report, records, init_pay, context=None):
        # 2016-11-2 支持了图片
        # 1.导入依赖，python3语法
        # from . import report_helper
        # 2. 需要添加一个"tpl"属性获得模版对象
        tempname = tempfile.mkdtemp()
        temp_out_file = self.generate_temp_file(tempname)
        doc = DocxTemplate(misc.file_open(report.template_file).name)

        env = api.Environment(cr, uid, context)
        partner = env.get('partner').search([('id', '=', context.get('partner_id'))])
        simple_dict = {'partner_name': partner.name,
                       'from_date': context.get('from_date'),
                       'to_date': context.get('to_date'),
                       'report_line': [],
                       'init_pay': {},
                       'final_pay': {}}
        if not records:
            if init_pay:
                simple_dict['init_pay'] = init_pay
                simple_dict['final_pay'] = init_pay
            doc.render({'obj': simple_dict, 'tpl': doc}, report_helper.get_env())
            doc.save(temp_out_file)

            report_stream = ''
            with open(temp_out_file, 'rb') as input_stream:
                report_stream = input_stream.read()

            os.remove(temp_out_file)
            return report_stream, report.output_type

        data = DataModelProxy(records)
        for p_value in data:
            simple_dict['report_line'].append({
                'date': p_value.date,
                'name': p_value.name,
                'note': p_value.note,
                'amount': p_value.amount,
                'pay_amount': p_value.pay_amount,
                'discount_money': p_value.discount_money,
                'balance_amount': p_value.balance_amount
            })
        if data:
            simple_dict['init_pay'] = data[0].balance_amount - data[0].amount + data[0].pay_amount - data[
                0].discount_money
            simple_dict['final_pay'] = data[-1].balance_amount

        doc.render({'obj': simple_dict, 'tpl': doc}, report_helper.get_env())
        doc.save(temp_out_file)

        if report.output_type == 'pdf':
            temp_file = self.render_to_pdf(temp_out_file)
        else:
            temp_file = temp_out_file

        report_stream = ''
        with open(temp_file, 'rb') as input_stream:
            report_stream = input_stream.read()

        os.remove(temp_file)
        return report_stream, report.output_type
