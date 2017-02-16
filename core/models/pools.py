# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.website.models.website import slug
from odoo import SUPERUSER_ID


# slug方法代理
def _slug(model, record_id):
    cr, uid, context, pool = request.env.cr, request.env.uid, request.env.context, request.registry

    record = pool.get(model).browse(cr, uid, record_id, context=context)
    return slug(record)


# 方法代理
class MethodProxy():
    def __init__(self, model, method):
        self.model = model
        self.method = method

    def __call__(self, *args, **kwargs):
        return getattr(self.model, self.method)(request.cr, SUPERUSER_ID, *args, **kwargs)


# 模型代理
class ModelProxy():
    def __init__(self, model):
        self.model = model

    def __getattr__(self, method):
        return MethodProxy(self.model, method)


# 模型池
class ModelPool():
    def __init__(self):
        self.pools_map = {}

    def __getitem__(self, model):
        return self.get(model)

    def get(self, model):
        registry = request.registry
        return ModelProxy(registry[model])
        # if not self.pools_map.has_key(model):
        #     registry = request.registry
        #     self.pools_map[model] = ModelProxy(registry[model])
        # return self.pools_map.get(model)


class CursorProxy():
    def __init__(self):
        pass

    def dictfetchone(self, *args):
        request.cr.execute(*args)
        return request.cr.dictfetchone()

    def dictfetchall(self, *args):
        request.cr.execute(*args)
        return request.cr.dictfetchall()


class PageProxy():
    def __init__(self):
        pass

    def render(self, page):
        values = {
            'path': page
        }
        try:
            website_page = 'website.%s' % page
            # template = request.website.get_template(website_page)
            html = request.render(website_page, values).render()
            pos_start = html.find('<main>')
            pos_end = html.find('</main>')
            if pos_start > 0 and pos_end > 0:
                html = html[pos_start + 7: pos_end]
                return html
        except ValueError:
            raise Exception(u"没有定义页面/page/" + page)

# 常用函数
common_functions = {
            'abs': abs,
            'chr': chr,
            'cmp': cmp,
            'float': float,
            'int': int,
            'len': len,
            'long': long,
            'map': map,
            'str': str
        }
