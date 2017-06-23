
odoo.define('web.WebTreeBackColor', function (require) {
    "use strict";
    var core = require('web.core');
    var session = require('web.session');
    var formats = require('web.formats');
    var QWeb = core.qweb;
    var list_widget_registry = core.list_widget_registry;

    var WebTreeBackColor = list_widget_registry.get('field').extend({
        format: function (row_data, options) {
            var self = this;

            // 显示内容格式化
            self.widget=null;
            var value = this._super.apply(self, arguments);

            // 增加背景色
            var ret = QWeb.render('ListView.row.bgcolor', {widget: this, value: value});

            //修改显示大小
            if (self.bgsize !== null || self.bgsize !== undefined || self.bgsize !== ''){
                return '<h'+self.bgsize+'>'+ret+'</h'+self.bgsize+'>';
            }
        }
    });

    list_widget_registry
    .add('field.bgcolor', WebTreeBackColor)
});
