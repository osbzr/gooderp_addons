
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
            var bgcolor = self.bgcolor;

            var bg_condition = self.bg_condition;

            if (self.bg_select !== null && self.bg_select !== undefined && self.bg_select !== ''){
                var bg_select = JSON.parse(self.bg_select);
                for(var key in bg_select){  
                    console.log("key:%s",key);
                }
                this.bgcolor = bg_select[value]
            }

            // 增加背景色
            if (this.bgcolor == null || this.bgcolor == undefined || this.bgcolor == ''){
                return value;
            }

            var ret = QWeb.render('ListView.row.bgcolor', {widget: this, value: value});

            //修改显示大小
            if (this.bgsize !== null && this.bgsize !== undefined && self.bgsize !== ''){
                return '<h'+this.bgsize+'>'+ret+'</h'+this.bgsize+'>';
            }
        }
    });

    list_widget_registry
    .add('field.bgcolor', WebTreeBackColor)
});
