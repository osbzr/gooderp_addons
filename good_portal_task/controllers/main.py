# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.good_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    @http.route()
    def account(self, **kw):
        """ Add task documents to main account page """
        response = super(WebsiteAccount, self).account(**kw)
        Project = request.env['project']
        Tasks = request.env['task']

        task_count = 0
        for project in Project.search([('customer_id', '=', request.env.user.gooderp_partner_id.id)]):
            task_count += Tasks.search_count([
                ('project_id', '=', project.id)
            ])

        response.qcontext.update({
            'task_count': task_count,
        })
        return response

    #
    # Tasks
    #
    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def tasks_my_orders(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        Task_obj = request.env['task']
        Project_obj = request.env['project']

        project_lists = []
        for project in Project_obj.search([('customer_id', '=', request.env.user.gooderp_partner_id.id)]):
            project_lists.append(project.id)

        domain = [
            ('project_id', 'in', project_lists)
        ]

        archive_groups = self._get_archive_groups('task', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        task_count = Task_obj.search_count(domain)

        # pager
        pager = request.website.pager(
            url="/my/tasks",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        tasks = Task_obj.search(
            domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'tasks': tasks,
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/tasks',
        })
        return request.render("good_portal_task.portal_my_tasks", values)

    @http.route(['/my/tasks/<int:order>'], type='http', auth="user", website=True)
    def tasks_followup(self, order=None, **kw):
        task = request.env['task'].browse([order])
        try:
            task.check_access_rights('read')
            task.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        task_sudo = task.sudo()

        return request.render("good_portal_task.tasks_followup", {
            'task': task_sudo,
        })
