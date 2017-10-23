# -*- coding: utf-8 -*-
import functools


def safe_division(divisor, dividend):
    return dividend != 0 and divisor / dividend or 0


def create_name(method):
    @functools.wraps(method)
    def func(self, vals):
        if vals.get('name', '/') == '/':
            vals.update(
                {'name': self.env['ir.sequence'].next_by_code(self._name) or '/'})

        return method(self, vals)

    return func


def create_origin(method):
    @functools.wraps(method)
    def func(self, vals):
        if hasattr(self, 'get_move_origin'):
            vals.update({'origin': self.get_move_origin(vals)})
        else:
            vals.update({'origin': self._name})

        return method(self, vals)

    return func


def inherits_after(res_back=True):
    def wrapper(method):
        @functools.wraps(method)
        def func(self, *args, **kwargs):

            res_before = execute_inherits_func(
                self, method.func_name, args, kwargs)
            res_after = method(self, *args, **kwargs)

            if res_back:
                return res_after
            else:
                return res_before

        return func
    return wrapper


def inherits(res_back=True):
    def wrapper(method):
        @functools.wraps(method)
        def func(self, *args, **kwargs):

            res_after = method(self, *args, **kwargs)
            if not res_back or (not isinstance(res_after, dict) or (isinstance(res_after, dict) and not(res_after.get('res_model') and res_after.get('view_type')))):
                res_before = execute_inherits_func(
                    self, method.func_name, args, kwargs)

            if res_back:
                return res_after
            else:
                return res_before

        return func
    return wrapper


def execute_inherits_func(self, method_name, args, kwargs):
    if self._inherits and len(self._inherits) != 1:
        raise ValueError(u'错误，当前对象不存在多重继承，或者存在多个多重继承')

    model, field = self._inherits.items()[0]
    values = self.read([field])
    field_ids = map(lambda value: value[field][0], values)

    models = self.env[model].browse(field_ids)
    return getattr(models, method_name)(*args, **kwargs)
