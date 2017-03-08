//-*- coding: utf-8 -*-
//############################################################################
//
//   OpenERP, Open Source Management Solution
//   This module copyright (C) 2015 Therp BV <http://therp.nl>.
//
//   This program is free software: you can redistribute it and/or modify
//   it under the terms of the GNU Affero General Public License as
//   published by the Free Software Foundation, either version 3 of the
//   License, or (at your option) any later version.
//
//   This program is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//   GNU Affero General Public License for more details.
//
//   You should have received a copy of the GNU Affero General Public License
//   along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//############################################################################

odoo.define('web_dashboard_open_action', function (require) {
    "use strict";
    var core = require('web.core');
    var pyeval = require('web.pyeval');

    core.form_tag_registry.get('board').include({
        on_load_action: function(result, index, action_attrs)
        {
            var self = this, action = _.extend({flags: {}}, result);
            action.context_string = action_attrs.context;
            action.domain_string = action_attrs.domain;
            action.context = pyeval.eval(
                'contexts', [action.context || {}, action_attrs.context || {}]);
            action.domain = pyeval.eval(
                'domains', [action_attrs.domain || [], action.domain || []],
                action.context);
            jQuery('#' + this.view.element_id + '_action_' + index)
                .parent()
                .find('.oe_web_dashboard_open_action')
                .click(function()
                {
                    self.do_action(action);
                });
            return this._super.apply(this, arguments);
        },
    });
})
