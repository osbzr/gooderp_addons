# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.osv import osv, fields as osv_fields
from xml.etree import ElementTree
import itertools
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


class MobileView(models.Model):
    _name = 'mobile.view'
    _order = 'sequence asc'

    MAP_OPERATOR = {
        '>': u'大于', '<': u'小与', '>=': u'大于等于',
        '<=': u'小与等于', '=': u'等于', '!=': u'不等于',
    }

    WIZARD_TYPE = [
        'many2one', 'number', 'date',
        'datetime', 'char', 'text',
    ]

    @api.one
    @api.depends('arch')
    def _get_using_wizard(self):
        tree = ElementTree.parse(StringIO(self.arch.encode('utf-8')))
        for wizard_node in tree.findall('.//wizard/field'):
            self.using_wizard = True
            return

        self.using_wizard = False

    display_name = fields.Char(u'菜单名称', required=True, copy=False)
    name = fields.Char(u'名称', required=True, copy=False)
    model = fields.Char(u'Model', required=True)
    icon_class = fields.Char('Icon Class')
    domain = fields.Char('domain')
    limit = fields.Integer(u'初始数量', default=20)
    sequence = fields.Integer(u'排序', default=16)
    using_wizard = fields.Boolean(compute='_get_using_wizard', string='启动wizard')
    arch = fields.Text(u'XML视图', required=True)

    _sql_constraints = [
        ('Unique name', 'unique(name)', u'名称必须唯一')
    ]

    @api.one
    @api.constrains('arch', 'model')
    def _check_seats_limit(self):
        try:
            self.env[self.model]
        except KeyError:
            raise osv.except_osv(u'错误', u'Model %s不存在' % self.model)

        try:
            tree = ElementTree.parse(StringIO(self.arch.encode('utf-8')))
        except:
            raise osv.except_osv(u'错误', u'遇到了一个无法解析的XML视图')

        tree_nodes = [node for node in tree.findall('.//tree/field')]
        if len(tree_nodes) != 3:
            raise osv.except_osv(u'错误', u'XML视图中tree标签下面的field标签必须是3个字段')

        for wizard_node in tree.findall('.//wizard/field'):
            attrib = wizard_node.attrib
            if not attrib.get('type') or attrib.get('type') not in self.WIZARD_TYPE:
                raise osv.except_osv(u'错误', u'wizard里面的field标签type属性必须存在或type属性值错误')

        columns = self.env[self.model].fields_get()
        for node in itertools.chain(tree.findall('.//tree/field'),
                                    tree.findall('.//form/field'),
                                    tree.findall('.//search/field')):
            if 'name' not in node.attrib or 'string' not in node.attrib:
                raise osv.except_osv(u'错误', u'每个field标签都必须要存在name和string属性')

            if node.attrib.get('name') not in columns:
                raise osv.except_osv(u'错误', u'字段属性%s未定义' % node.attrib.get('name'))

            if node.attrib.get('operator'):
                if node.attrib.get('operator') not in self.MAP_OPERATOR:
                    raise osv.except_osv(u'错误', u'不能识别的操作符%s' % node.attrib.get('operator'))

    def map_operator(self, operator):
        return self.MAP_OPERATOR.get(operator, '')

    def column_type(self, field):
        return self.env[self.model]._columns[field]._type
