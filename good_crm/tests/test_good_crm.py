# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestGoodCrm(TransactionCase):

    def setUp(self):
        """ SetUp Data """
        super(TestGoodCrm, self).setUp()
        self.opportunity = self.env['opportunity'].create({
            'task_id': self.env.ref('task.task_sell').id,
            'planned_revenue': 10000,
        })

    def test_assign_to_me(self):
        """ assign_to_me """
        self.opportunity.assign_to_me()
