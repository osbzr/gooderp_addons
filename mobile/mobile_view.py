# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.osv import osv, fields as osv_fields
from xml.etree import ElementTree
from openerp.tools.safe_eval import safe_eval as eval
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
        'datetime', 'char', 'text', 'selection'
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
    using_wizard = fields.Boolean(compute='_get_using_wizard', string=u'启动wizard')
    arch = fields.Text(u'XML视图', required=True)

    _sql_constraints = [
        ('Unique name', 'unique(name)', u'名称必须唯一')
    ]

    def _check_selection(self, attrib):
        if attrib.get('type') == 'selection':
            if not attrib.get('selection'):
                raise osv.except_osv(u'错误', u'selection类型的字段需要指定该字段的selection属性')

            try:
                selection = eval(attrib.get('selection'))
                if not isinstance(selection, list):
                    raise ValueError()

                for item in selection:
                    if not isinstance(item, (list, tuple)):
                        raise ValueError()

                    if len(item) != 2:
                        raise ValueError()
            except:
                raise osv.except_osv(u'错误', u'无法解析的selection属性%s' % attrib.get('selection'))

    def _check_domain(self, model, domain):
        try:
            model_columns = self.env[model].fields_get()
            domain = eval(domain)
            if not isinstance(domain, list):
                raise ValueError()

            for item in domain:
                if item == '|':
                    continue

                if not isinstance(item, (list, tuple)):
                    raise ValueError()

                if item[0] not in model_columns:
                    raise ValueError()

                if len(item) != 3:
                    raise ValueError()
        except:
            raise osv.except_osv(u'错误', u'无法解析的domain条件%s' % domain)

    def _check_model(self, model):
        try:
            self.env[model]
        except KeyError:
            raise osv.except_osv(u'错误', u'Model %s不存在' % model)

    def _check_many2one(self, attrib):
        if attrib.get('type') == 'many2one':
            if not attrib.get('model'):
                raise osv.except_osv(u'错误', u'many2one类型的字段需要指定该字段的model')

            self._check_model(attrib.get('model'))
            self._check_domain(attrib.get('model'), attrib.get('domain'))

    def _check_wizard(self, tree):
        for wizard_node in tree.findall('.//wizard/field'):
            attrib = wizard_node.attrib
            if not attrib.get('type') or attrib.get('type') not in self.WIZARD_TYPE:
                raise osv.except_osv(u'错误', u'wizard里面的field标签type属性必须存在或type属性值错误')

            self._check_many2one(attrib)
            self._check_selection(attrib)

    def _check_field(self, tree):
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

    @api.one
    @api.constrains('domain')
    def check_domain(self):
        if self.domain:
            self._check_domain(self.model, self.domain)

    @api.one
    @api.constrains('model')
    def check_model(self):
        self._check_model(self.model)

    @api.one
    @api.constrains('arch', 'model')
    def _check_seats_limit(self):
        self._check_model(self.model)

        try:
            tree = ElementTree.parse(StringIO(self.arch.encode('utf-8')))
        except:
            raise osv.except_osv(u'错误', u'遇到了一个无法解析的XML视图')

        tree_nodes = [node for node in tree.findall('.//tree/field')]
        if len(tree_nodes) != 3:
            raise osv.except_osv(u'错误', u'XML视图中tree标签下面的field标签必须是3个字段')

        self._check_wizard(tree)
        self._check_field(tree)

    def map_operator(self, operator):
        return self.MAP_OPERATOR.get(operator, '')

    def column_type(self, field):
        return self.env[self.model]._columns[field]._type
