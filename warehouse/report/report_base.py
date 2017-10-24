# -*- coding: utf-8 -*-

from odoo.osv import osv
from odoo.http import request
import itertools
import operator
import time
import pickle
from odoo import models, api
from odoo.exceptions import UserError


class ReportBase(models.Model):
    _name = 'report.base'
    _description = u'使用search_read来直接生成数据的基本类，其他类可以直接异名继承当前类来重用搜索、过滤、分组等函数'

    _expired_time = 60
    _cache_record = False
    _cache_env = False
    _cache_time = False

    def select_sql(self, sql_type='out'):
        return ''

    def from_sql(self, sql_type='out'):
        return ''

    def where_sql(self, sql_type='out'):
        return ''

    def group_sql(self, sql_type='out'):
        return ''

    def order_sql(self, sql_type='out'):
        return ''

    def get_context(self, sql_type='out', context=None):
        return {}

    def execute_sql(self, sql_type='out'):
        context = self.get_context(sql_type, context=self.env.context)
        for key, value in context.iteritems():
            if isinstance(context[key], basestring):
                context[key] = value.encode('utf-8')

        self.env.cr.execute((self.select_sql(sql_type) + self.from_sql(sql_type) + self.where_sql(
            sql_type) + self.group_sql(sql_type) + self.order_sql(
            sql_type)).format(**context))

        return self.env.cr.dictfetchall()

    def collect_data_by_sql(self, sql_type='out'):
        return []

    def check_valid_domain(self, domain):
        if not isinstance(domain, (list, tuple)):
            raise UserError(u'不可识别的domain条件，请检查domain"%s"是否正确' % str(domain))

    def _get_next_domain(self, domains, index):
        domain = domains[index]
        if domain == '|':
            _, index = self.get_next_or_domain(domains, index + 1)
        else:
            index += 1
            self.check_valid_domain(domain)

        return index

    def get_next_or_domain(self, domains, index):
        index = self._get_next_domain(domains, index)

        return index, self._get_next_domain(domains, index)

    def _process_domain(self, result, domain):
        if domain and len(domain) == 3:
            field, opto, value = domain

            compute_operator = {
                'ilike': lambda field, value: unicode(value).lower() in unicode(field).lower(),
                'like': lambda field, value: unicode(value) in unicode(field),
                'not ilike': lambda field, value: unicode(value).lower() not in unicode(field).lower(),
                'not like': lambda field, value: unicode(value) not in unicode(field),
                'in': lambda field, value: field in value,
                'not in': lambda field, value: field not in value,
                '=': operator.eq,
                '!=': operator.ne,
                '>': operator.gt,
                '<': operator.lt,
                '>=': operator.ge,
                '<=': operator.le,
            }

            opto = opto.lower()
            if field in result:
                if opto in compute_operator.iterkeys():
                    return compute_operator.get(opto)(result.get(field), value)

                raise UserError(u'暂时无法解析的domain条件%s，请联系管理员' % str(domain))

        raise UserError(u'不可识别的domain条件，请检查domain"%s"是否正确' % str(domain))

    def _compute_domain_util(self, result, domains):
        index = 0
        while index < len(domains):
            domain = domains[index]
            index += 1
            if domain == '|':
                left_index, right_index = self.get_next_or_domain(
                    domains, index)

                if not self._compute_domain_util(result, domains[index:left_index]) and not self._compute_domain_util(result, domains[left_index:right_index]):
                    return False

                index = right_index
            else:
                self.check_valid_domain(domain)
                if not self._process_domain(result, domain):
                    return False

        return True

    def _compute_domain(self, result, domain):
        return filter(lambda res: self._compute_domain_util(res, domain), result)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=80, orderby=False, lazy=True):

        def dict_plus(collect, values):
            for key, value in values.iteritems():
                if isinstance(value, (long, int, float)):
                    if key not in collect:
                        collect[key] = 0
                    collect[key] += value

            collect[groupby[0] + '_count'] += 1

            return collect

        res = []
        values = self.search_read(
            domain=domain, fields=fields, offset=offset, limit=limit or 80, order=orderby)

        if groupby:
            key = operator.itemgetter(groupby[0])
            for group, itervalue in itertools.groupby(sorted(values, key=key), key):
                collect = {'__domain': [
                    (groupby[0], '=', group)], groupby[0]: group, groupby[0] + '_count': 0}
                collect = reduce(lambda collect, value: dict_plus(
                    collect, value), itervalue, collect)

                if len(groupby) > 1:
                    collect.update({
                        '__context': {'group_by': groupby[1:]}
                    })

                if domain:
                    collect['__domain'].extend(domain)

                res.append(collect)

        return res

    def _compute_order(self, result, order):
        # TODO 暂时不支持多重排序
        if order:
            order = order.partition(',')[0].partition(' ')
            result.sort(key=lambda item: item.get(
                order[0]), reverse=order[2] == 'ASC')

        return result

    def _compute_limit_and_offset(self, result, limit, offset):
        return result[offset:limit + offset]

    def update_result_none_to_false(self, result):
        for val in result:
            for key, value in val.iteritems():
                if value is None:
                    val[key] = False

        return result

    def get_data_from_cache(self, sql_type='out'):
        if self._cache_env != (self.env.uid, self.env.context) \
                or not self._cache_record or self._cache_time + self._expired_time < time.time():

            self.__class__._cache_record = self.update_result_none_to_false(
                self.collect_data_by_sql(sql_type))
            self.__class__._cache_time = time.time()
            self.__class__._cache_env = (self.env.uid, self.env.context)

        return self._cache_record

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=80, order=None):
        result = self.get_data_from_cache(sql_type='out')

        result = self._compute_domain(result, domain)
        result = self._compute_order(result, order)
        result = self._compute_limit_and_offset(result, limit, offset)

        return result

    @api.model
    def search_count(self, domain):
        result = self.get_data_from_cache(sql_type='out')
        result = self._compute_domain(result, domain)

        return len(result)

    @api.multi
    def read(self, fields=None, context=None, load='_classic_read'):
        res = []
        fields = fields or []

        fields.append('id')
        for record in self.get_data_from_cache():
            if record.get('id') in self.ids:
                res.append({field: record.get(field) for field in fields})

        return res
