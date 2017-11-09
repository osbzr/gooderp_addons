# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval as eval
from datetime import datetime


class HomeReportType(models.Model):
    _name = "home.report.type"
    _description = u"用来分类报表,让相似的报表显示在一起"
    name = fields.Char(u'报表类别', help=u'在home.page 中报表类别不同类别的可以分组,组别的名称!')
    sequence = fields.Integer(u'序列', help=u'在home.page 中报表类别分组 时的顺序进行调整!')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class HomePage(models.Model):
    _name = "home.page"
    _rec_name = "note_one"
    _description = u"本模块就是一些常用操作的集合,也是小量级各方数据显示的平台！"
    _order = "sequence"

    sequence = fields.Integer(u'序号', help=u'用来确定 每条记录在首页中的显示的顺序(而不仅仅是记录的顺序)')
    action = fields.Many2one('ir.actions.act_window', string=u'动作', required='1', help=u'设置首页点击事件,\
                                                                                         跳转对应的模型action')
    menu_type = fields.Selection([(u'all_business', u'主要功能'), (u'amount_summary', u'关键指标'), (u'report', u'常用报表')],
                                 string=u'类型', required="1", help=u'选定本条记录的类型,本字段会决定本条记录属于那一块')
    domain = fields.Char(u'过滤', default='[]',
                         help=u'字符串条件,用来过滤出您所选的视图中的数据!')
    note_one = fields.Char(u'名称', help=u'在首页中的相应的文字显示内容')
    compute_field_one = fields.Many2one('ir.model.fields', string=u'计算字段', help=u'在首页中有用于数字显示的元素的,\
                                                            仅适合小量数据的计算数字对应的视图或模型中的字段!')
    compute_type = fields.Selection([(u'sum', u'sum'), (u'average', u'average')], default="sum", string=u"计算方式",
                                    help=u'对于所选的计算字段的计算方式!注:目前只支持sum')
    context = fields.Char(u'上下文', help=u'对应跳转视图传进去的参数!')
    is_active = fields.Boolean(
        u'可用', default=True, help=u'为了方便调试,首页美观性,或临时性替换首页元素!')
    report_type_id = fields.Many2one('home.report.type', string='报表类别', help=u'类型为 常用报表时 要选择报表类别,\
                                    可以对不同类型的报表进行分组!')
    group_ids = fields.Many2many(
        'res.groups', 'home_page_group_rel', 'home_page_id', 'group_id', string='用户组')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.onchange('action')
    def onchange_action(self):
        if self.action:
            return {
                'domain': {'view_id': [('model', '=', self.action.res_model), ('type', '=', 'tree')], }
            }

    def constract_action_vals(self, action):
        """
        通过填写的自定义的action，构造出要用到的action的参数
        :param action:
        :return:  view_id 从action上读取，如果为空则 视图取默认值！
        """
        views_ids = [view.view_id.id for view in action.action.view_ids]
        note_one, view_mode, res_model = action.note_one, action.action.view_mode, action.action.res_model
        domain, action_id, context, view_id = action.action.domain, action.id, action.action.context, \
            views_ids or False
        action_name, target = action.action.name, action.action.target
        return [note_one, view_mode, res_model, domain, context, view_id, action_name, target]

    @api.model
    def construction_action_url_list(self, action, action_url_list):
        """
        把所有的数据整合，经过深度处理放进 action_url_list
        :param action: [home.page]对象，数据的来源。
        :param action_url_list: 存放数据的处理结果。
        :return:
        """
        action_vals = self.constract_action_vals(action)
        if action.menu_type == 'all_business':
            action_url_list['main'].append(action_vals)
        elif action.menu_type == 'amount_summary':
            # 金额汇总类
            compute_domain = eval(action.domain or '[]')
            res_model_objs = self.env[action.action.res_model].search(
                compute_domain)
            field_compute = action.compute_field_one.name
            # 最新的金额
            compute_value = sum([res_model_obj[field_compute]
                                 for res_model_obj in res_model_objs])
            # 返回结果
            action_vals[0] = "%s  %s" % (action_vals[0], compute_value)
            action_url_list['top'].append(action_vals)
        else:
            action_vals[0] = "%s   " % action_vals[0]
            type_sequence_str = "%s;%s" % (
                action.report_type_id.sequence, action.report_type_id.name)
            if action_url_list['right'].get(type_sequence_str):
                action_url_list['right'][type_sequence_str].append(action_vals)
            else:
                action_url_list['right'].update(
                    {type_sequence_str: [action_vals]})

    @api.model
    def get_action_url(self):
        """
        搜索设置表中的数据, 然后分组,
        :return: 返回符合格式的数据, 方便前端 的解析返回一个字典  key 为 all_business amount_summary
        [显示的名称,  对应的跳转的视图类型, 跳转的视图的模型 , 跳转视图的context参数, 跳转视图的id, 跳转视图的名称]
        key 为 report 内容为一个字典 key 为('report顺序;report name':[显示的名称,
        对应的跳转的视图类型, 跳转的视图的模型 , 跳转视图的context参数, 跳转视图的id, 跳转视图的名称])
        """
        action_url_list = {'main': [], 'top': [], 'right': {}}
        user_row = self.env.user
        user_group_list = set([group.id for group in user_row.groups_id])
        action_list = self.env['home.page'].search([(1, '=', 1), ('sequence', '!=', 0),
                                                    ('is_active', '=', True)], order='sequence')
        for action in action_list:
            if not [group.id for group in action.group_ids] or\
                    list(set([group.id for group in action.group_ids]).intersection(user_group_list)):
                self.construction_action_url_list(action, action_url_list)
        action_url_list['right'] = sorted(
            action_url_list['right'].items(), key=lambda d: d[0])
        return action_url_list
