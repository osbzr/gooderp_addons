# -*- coding: utf-8 -*-
from openerp import api, fields, models


class home_page(models.Model):
    _name = "home.page"
    _rec_name = "action"

    sequence = fields.Integer(u'序列')
    action = fields.Many2one('ir.actions.act_window', string='快捷页面', required='1')
    view_id = fields.Many2one('ir.ui.view', string='对应的视图')
    image = fields.Binary(u"显示的图片")
    menu_type = fields.Selection([(u'main', u'主菜单'), (u'top', u'金额汇总'), (u'left', u'快速查看')], string='类型', required="1")
    domain = fields.Char(u'页面的过滤', default='[]')
    note_one = fields.Char(u'第一个显示名称')
    compute_field_one = fields.Many2one('ir.model.fields', string='需要计算的字段')
    note_two = fields.Char(u'显示名称')
    compute_field_two = fields.Many2one('ir.model.fields', string='需要计算的字段')
    compute_type = fields.Selection([(u'sum', u'sum'), (u'average', u'average')], default="sum", string="计算类型")
    context = fields.Char(u'动作的上下文')

    @api.onchange('action')
    def onchange_action(self):
        if self.action:
            return {
                'domain': {'view_id': [('model', '=', self.action.res_model), ('type', '=', 'tree')], }
            }

    @api.model
    def get_action_url(self):
        action_url_lsit = {'main': [], 'top': [], 'right': []}

        action_list = self.env['home.page'].search([(1, '=', 1), ('sequence', '!=', 0)], order='sequence')
        for action in action_list:
            if action:
                if action.menu_type == 'main':
                    action_url_lsit['main'].append([action.note_one, action.action.view_mode, action.action.res_model,
                                                    action.action.domain, action.id, action.action.context,
                                                    action.view_id.id, action.action.name])
                elif action.menu_type == 'top':
                    note = ""
                    res_model_objs = self.env[action.action.res_model].search(eval(action.domain or '[]'))
                    if action.compute_field_one and action.compute_field_two:
                        note = "%s  %s <br\> %s  %s" % (action.note_one, sum([res_model_obj[action.compute_field_one.name] for res_model_obj in res_model_objs]),
                                                        action.note_two, sum([res_model_obj[action.compute_field_two.name] for res_model_obj in res_model_objs]))
                    elif action.compute_field_one or action.compute_field_two:
                        field_compute, note = "", ""
                        if action.compute_field_one:
                            field_compute = action.compute_field_one.name
                            note = action.note_one
                        else:
                            field_compute = action.compute_field_two.name
                            note = action.note_two
                        note = "%s  %s" % (note, sum([res_model_obj[field_compute] for res_model_obj in res_model_objs]))

                    else:
                        note = "%s  %s" % (action.note_one, sum([1 for res_model_obj in res_model_objs]))

                    action_url_lsit['top'].append([note, action.action.view_mode, action.action.res_model, action.domain,
                                                   action.context, action.view_id.id, action.action.name])
                else:
                    res_model_objs = self.env[action.action.res_model].search(eval(action.domain or '[]'))
                    action_url_lsit['right'].append(["%s  %s" % (action.note_one, sum([1 for res_model_obj in res_model_objs])),
                                                     action.action.view_mode, action.action.res_model,
                                                     action.domain, action.context, action.view_id.id, action.action.name])
        return action_url_lsit
