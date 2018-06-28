# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestIrSequence(TransactionCase):

    def test_get_next_char(self):
        '''序列号自动重置'''
        seq = self.env['ir.sequence'].with_context({
            'ir_sequence_date': '2018-04-01',
            'ir_sequence_date_range': '2018-05-01',
        }).create({
            'number_next': 1,
            'padding': 4,
            'number_increment': 1,
            'implementation': 'standard',
            'name': 'test-sequence',
            'auto_reset': True,
            'reset_period': 'month',
            'reset_init_number': 1,
        })
        seq.next_by_id()
        n = seq.next_by_id()
        self.assertEqual(n, "0002")
        seq.reset_time = '00'   # current_time = '04'，二者不等即可自动重置
        n = seq.next_by_id()
        self.assertEqual(n, "0001")