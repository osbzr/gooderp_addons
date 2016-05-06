# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.osv import osv
from xml.etree import ElementTree
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


class MobileView(models.Model):
    _name = 'mobile.view'
    _order = 'sequence desc'

    display_name = fields.Char(u'菜单名称', required=True, copy=False)
    name = fields.Char(u'名称', required=True, copy=False)
    model = fields.Char(u'Model', required=True)
    icon_class = fields.Char('Icon Class')
    domain = fields.Char('domain')
    limit = fields.Integer(u'初始数量', default=20)
    sequence = fields.Integer(u'排序', default=16)
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

        columns = self.env[self.model]._columns
        for node in tree.findall('.//field'):
            if 'name' not in node.attrib or 'string' not in node.attrib:
                raise osv.except_osv(u'错误', u'每个field标签都必须要存在name和string属性')

            if node.attrib.get('name') not in columns:
                print 'shit', node.attrib.get('name')
                raise osv.except_osv(u'错误', u'字段属性%s未定义' % node.attrib.get('name'))
