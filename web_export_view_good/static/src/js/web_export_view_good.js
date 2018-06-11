//  @@@ web_export_view custom JS @@@
//#############################################################################
//   Copyright (C) 2016 开阖有限公司 (<http://www.osbzr.com>)(学习原oca模块 web_export_view)
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as published
//    by the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.
//
//    This program is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//#############################################################################

odoo.define('web_export_view_good.web_export_view_good', function (require) {
"use strict";

var framework = require('web.framework');
var ListView = require('web.ListView');
var formats = require('web.formats');
var Model = require('web.DataModel');
function compute_main_data(rows,export_columns_keys){
    var export_rows = []

    $.each(rows, function () {
        var $row = $(this);
        if ($row.attr('data-id')) {
            var export_row = [];
            /*var checked = $row.find('td input[type=checkbox]');*/
            /*if (checked.get(0).checked) {*/
            var export_columns_dict={};
            $.each(export_columns_keys, function () {
                var column =this;
                if (export_columns_dict[column]!=undefined){
                    export_columns_dict[column]=export_columns_dict[column]+1;
                }else{
                     export_columns_dict[column] = 0;}
                var cell = $row.find('td[data-field="' + column + '"]').get(export_columns_dict[column]);
                var cell_object =$row.find('td[data-field="' + column + '"]');
                var text = cell.text || cell.textContent || cell.innerHTML || "";
                var is_boolean_cell = cell_object.find('.o_checkbox input[type=checkbox]');
                if (cell.classList.contains("oe_list_field_float")||cell.classList.contains("o_list_number")||cell.classList.contains("oe_number")) {
                    export_row.push(formats.parse_value(text.replace('^[\-]?[0-9]/g', ''), {'type': "float"}, 0));
                }else if (is_boolean_cell.length>0) {
                    if (is_boolean_cell.get(0).checked) {
                        export_row.push('√');
                    }
                    else {
                        export_row.push('X');
                    }
                } else {
                    if (cell.innerHTML){
                         var no_tag_and_bank_row = cell.innerHTML.replace(/<\/?[^>]*>/g,'').replace(/[\r\n]/g,"")
                         if((no_tag_and_bank_row.split("                   ")).length>1){
                             var list_result = no_tag_and_bank_row.split("                   ");
                             text =list_result.splice(1,list_result.length).join("\r\n");
                            };
                    }
                    export_row.push(text.trim());
                }
            });
            export_rows.push(export_row);
            /*}*/
        }
    });

    return export_rows;
};
function compute_footer_data(amount,export_columns_keys) {
    var export_rows = []
    var footer = 0;
    $.each(amount, function () {
        var $row = $(this);
        var export_row =  new Array(export_columns_keys.length);;
        var index = 1;
        $.each(export_columns_keys, function () {
            var cell = $row.find('td').get(index);
            index = index + 1;
            if (cell){
                var text = cell.text || cell.textContent || cell.innerHTML || "";
                if (text.indexOf(" ") == -1) {
                     if (text!==''){
                        footer = 1;
                         // footer 数字类型的字符串转化成数字，显示时单元格内容会靠右显示
                        var cell_value = text.trim().split(",").join("");
                        export_row[index-2]=parseFloat(cell_value);}
                }else {
                    export_row[index-2]=text.trim();}
                }
        });
        if (footer == 1) {
            export_row[0] = "合计";
            export_rows.push(export_row);
        }
    });
    return export_rows
};

function button_export_action () {
    var self = this;
    var view = self;
    var export_columns_keys = [];
    var export_columns_names = [];
    var location = 0;
    var export_rows = [];
    $.each(view.visible_columns, function () {
        export_columns_keys.push(this.id);
        export_columns_names.push(this.string);
        // 找到 查看明细 按钮所在的位置
        if (this.tag == 'button' && this.string == '查看明细') {
            location = export_columns_keys.length
        }
    });
    export_rows.push(export_columns_names);
    var rows = view.$el.find('.o_list_view > tbody > tr');
    export_rows = export_rows.concat(compute_main_data(rows,export_columns_keys));
    var amount = view.$el.find('.o_list_view > tfoot > tr');
    export_rows = export_rows.concat(compute_footer_data(amount,export_columns_keys));
    // 排除掉 查看明细 按钮所在的列
    if (location != 0) {
        for (var i = 0; i < export_rows.length; i++) {
            export_rows[i].splice(location-1, 1);
        }
    }
    new Model('report.template').call('get_time', [this.model], {
                context: this.dataset.context
            }).done(function (data) {
                var now_day = data[0];
                var operation_message = new Array(export_columns_names.length);
                var header = new Array(export_columns_names.length);
                for (var i = 0; i < operation_message.length; i++) { operation_message[i] = " "; }
                operation_message[0] = "操作人";
                operation_message[1] = view.getParent().session.username;
                operation_message[operation_message.length - 2] = "操作时间";
                operation_message[operation_message.length - 1] = now_day.trim();
                export_rows.push(operation_message);
                for(var i=0;i<data[3];i++){
                    export_rows.splice(i, 0, []);
                }
                if (view.dataset.context.attachment_information !== undefined) {
                    var arr = view.dataset.context.attachment_information.split(",");
                    var newArray = [];
                    for (var i = 0; i < arr.length; i++) {
                        var arrOne = arr[i];
                        newArray.push(arrOne);
                    }
                    export_rows.splice(0, 0, newArray);
                }
                for(var i=0;i<data[2];i++){
                    export_rows.splice(i, 0, []);
                }
                header[0] =  view.name

                $.blockUI();
                view.session.get_file({
				                url: '/web/export/export_xls_view',
				                data: {
                        data: JSON.stringify({
                            model: view.model,
                            headers: header,
                            files_name:view.ViewManager.title,
                            rows: export_rows,
                            file_address: data[1]
                        })
                    }, complete: $.unblockUI});
            });
        };
ListView.prototype.defaults.import_enabled = true;
ListView.include({
    render_buttons: function() {
        var self = this;
        var add_button = false;
        if (!this.$buttons) { // Ensures that this is only done once
            add_button = true;
        }
        this._super.apply(this, arguments); // Sets this.$buttons
        if(add_button) {
            this.$buttons.on('click', '.o_button_export', button_export_action.bind(this));
        }
    },
    set_default_options: function (options) {
        this._super(_.defaults(options || {}, {
            import_enabled: true,
        }));
    },
});});