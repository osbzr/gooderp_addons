
odoo.define('web.WebTreeBackColor', function (require) {
    "use strict";
    var core = require('web.core');
    var session = require('web.session');
    var QWeb = core.qweb;
    var list_widget_registry = core.list_widget_registry;

    var WebTreeBackColor = list_widget_registry.get('field').extend({
        format: function (row_data, options) {
            if (!row_data[this.id] || !row_data[this.id].value) {
                return '';
            }
            var value = row_data[this.id].value;
            if (this.type === 'Char' || this.type === 'Float'|| this.type === 'Integer'|| this.type === 'Selection'|| this.type === 'Many2one') {
                if (value && value.substr(0, 10).indexOf(' ') === -1) {
                    // The media subtype (png) seems to be arbitrary
                    value = value;

                }
            }
            return QWeb.render('ListView.row.bgcolor', {widget: this, value: value});
        }
    });

    list_widget_registry
    .add('field.bgcolor', WebTreeBackColor)
});
