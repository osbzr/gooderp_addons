# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval as eval

class home_report_type(models.Model):
    _name = "home.report.type"
    name = fields.Char(u'报表类别', help=u'在home.pagel 中报表类别不同类别的可以分组,组别的名称!')
    sequence = fields.Integer(u'序列', help=u'在home.pagel 中报表类别分组 时的顺序进行调整!')


class home_page(models.Model):
    _name = "home.page"
    _rec_name = "action"

    sequence = fields.Integer(u'序列', help=u'用来确定 每条记录在首页中的显示的顺序(而不仅仅是记录的顺序)')
    action = fields.Many2one('ir.actions.act_window', string=u'快捷页面', required='1', help=u'设置首页点击事假,的跳转的对应的模型的action')
    view_id = fields.Many2one('ir.ui.view', string=u'对应的视图', help=u'设置首页点击事假,的跳转的对应的模型的视图')
    menu_type = fields.Selection([(u'all_business', u'业务总览'), (u'amount_summary', u'金额汇总'), (u'report', u'实时报表')],
                                 string=u'类型', required="1", help=u'选定本条记录的类型,本字段会决定本条记录属于那一块')
    domain = fields.Char(u'页面的过滤', default='[]', help=u'字符串条件,用来过滤出您所选的视图中的数据!')
    note_one = fields.Char(u'第一个显示名称', help=u'在首页中的相应的文字显示内容')
    compute_field_one = fields.Many2one('ir.model.fields', string=u'需要计算的字段', help=u'在首页中有用于数字显示的元素的,数字对应的视图或模型中的字段!')
    compute_type = fields.Selection([(u'sum', u'sum'), (u'average', u'average')], default="sum", string=u"计算类型",
                                    help=u'对于所选的计算字段的计算方式!注:目前只支持sum')
    context = fields.Char(u'动作的上下文', help=u'对应跳转视图传进去的参数!')
    is_active = fields.Boolean(u'是否可用', default=True, help=u'为了方便调试,首页美观性,或临时性替换首页元素!')
    report_type_id = fields.Many2one('home.report.type', string='报表类别', help=u'类型为 实时报表时 要选择报表类别,可以对不同类型的报表进行分组!')
    group_ids = fields.Many2many('res.groups','home_page_group_rel','home_page_id','group_id',string='用户组')

    @api.onchange('action')
    def onchange_action(self):
        if self.action:
            return {
                'domain': {'view_id': [('model', '=', self.action.res_model), ('type', '=', 'tree')], }
            }

    @api.model
    def construction_action_url_list(self,action,action_url_list):
        if action.menu_type == 'all_business':
            action_url_list['main'].append([action.note_one, action.action.view_mode, action.action.res_model,
                                            action.action.domain, action.id, action.action.context,
                                            action.view_id.id, action.action.name, action.action.target])
        elif action.menu_type == 'amount_summary':
            res_model_objs = self.env[action.action.res_model].search(eval(action.domain or '[]'))
            field_compute = action.compute_field_one.name
            note = action.note_one
            note = "%s  %s" % (note, sum([res_model_obj[field_compute] for res_model_obj in res_model_objs]))
            action_url_list['top'].append([note, action.action.view_mode, action.action.res_model, action.domain,
                                           action.context, action.view_id.id, action.action.name, action.action.target])
        else:
            vals_list = ["%s   " % (action.note_one),
                         action.action.view_mode, action.action.res_model,
                         action.domain, action.context, action.view_id.id, action.action.name, action.action.target]
            type_sequence_str = "%s;%s" % (action.report_type_id.sequence, action.report_type_id.name)
            if action_url_list['right'].get(type_sequence_str):
                action_url_list['right'][type_sequence_str].append(vals_list)
            else:
                action_url_list['right'].update({type_sequence_str: [vals_list]})

    @api.model
    def get_action_url(self):
        """
        搜索设置表中的数据, 然后分组,
        :return: 返回符合格式的数据, 方便前端 的解析返回一个字典  key 为 all_business amount_summary
        [显示的名称,  对应的跳转的视图类型, 跳转的视图的模型 , 跳转视图的context参数, 跳转视图的id, 跳转视图的名称]
        key 为 report 内容为一个字典 key 为('report顺序;report name':[显示的名称,  对应的跳转的视图类型, 跳转的视图的模型 , 跳转视图的context参数, 跳转视图的id, 跳转视图的名称])
        """
        action_url_list = {'main': [], 'top': [], 'right': {}}
        user_row = self.env.user
        user_group_list = set([group.id for group in user_row.groups_id])
        action_list = self.env['home.page'].search([(1, '=', 1), ('sequence', '!=', 0),('is_active','=',True)], order='sequence')
        for action in action_list:
            if not [group.id for group in action.group_ids] or list(set([group.id for group in action.group_ids]).intersection(user_group_list)):
                self.construction_action_url_list(action,action_url_list)
        action_url_list['right'] = sorted(action_url_list['right'].items(), key=lambda d: d[0])
        return action_url_list
