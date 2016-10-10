odoo.define('num_to_china.NumberToChina', function(require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var form_widgets = require('web.form_widgets');
var Model = require('web.Model');
// Field in which the user can both type normally and scan barcodes

var NumberToChina = form_widgets.FieldFloat.extend({
    render_value: function () {
            var self = this
            if (!this.get("effective_readonly")) {
                this.$el.find('input').val(this.get('value'));
            } else {
                var num = this.get('value');
                new Model("res.currency").call("rmb_upper", [parseFloat(num)]).then(function (result) {
                    self.$el.text(result);
                });
            }
        },
    });
    core.form_widget_registry
    .add('num_to_china', NumberToChina)
})