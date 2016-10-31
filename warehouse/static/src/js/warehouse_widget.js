odoo.define('warehouse.warehouse', function (require) {
"use strict";
var ListView = require('web.ListView');
var FormView = require('web.FormView');
var form_relational = require('web.form_relational');
var data = require('web.data');
var Model = require('web.Model');
var menu = require('web.Menu');

FormView.include({
    start: function() {
        var self = this,
            res = this._super.apply(this, arguments);

        self.$el.on('keydown', '.ge_scan_barcode', function(event) {
            if (event.keyCode === 13) {
                var $this = $(this);
                return self.save().done(function(result) {
                    self.trigger("save", result);
                    self.reload().then(function() {
                        self.to_view_mode();
                        var menu = menu;
                        if (menu) {
                            menu.do_reload_needaction();
                        }
                    }).then(function() {
                        new Model("wh.move").call("scan_barcode",[self.model, $this.val(), self.datarecord.id]).then(
                            function() {
                                self.reload();
                                self.$el.find('input').val('');
                            }
                        );
                    }).then(function() {
                        $this.focus();
                    })
                });
            }
        })
    },
});
})

// odoo.warehouse = function(instance) {
//     instance.web.list.Column.include({
//         _format: function(row_data, options) {
//             if (this.widget === 'selection_clickable' && !_.isUndefined(this.selection)) {
//                 var field_name = row_data[this.id]['value'],
//                     select = _.find(this.selection, function(select) { return select[0] === field_name})
//
//                 if (_.isUndefined(select)) {
//                     delete this.widget;
//                     return this._super(row_data, options)
//                 }
//                 return _.str.sprintf("<span class='selection-clickable-mode' data-value=%s >%s</span>",
//                     select[0], select[1]);
//             } else if (this.widget === 'boolean_clickable') {
//                 console.warn('boolean_clickable', row_data, this);
//
//                 return _.str.sprintf("<span class='boolean-clickable-mode' data-value=%s>%s</span>",
//                     row_data[this.id]['value'],
//                     row_data[this.id]['value']? '已启用' : '已禁止');
//
//             } else {
//                 return this._super(row_data, options);
//             };
//
//         },
//     });
//
//     instance.web.ListView.List.include({
//         render: function() {
//             var self = this;
//                 result = this._super(this, arguments),
//
//             this.$current.delegate('span.selection-clickable-mode', 'click', function(e) {
//                     e.stopPropagation();
//                     var current = $(this),
//                         notify = instance.web.notification,
//                         data_id = current.closest('tr').data('id'),
//                         field_name = current.closest('td').data('field'),
//                         field_value = current.data('value'),
//                         model = new instance.web.Model(self.dataset.model);
//
//                     var column = _.find(self.columns, function(column) { return column.id === field_name})
//                     if (_.isUndefined(column)) {
//                         notify.notify('抱歉', '当前列表中没有定义当前字段');
//                         return;
//                     }
//
//                     var options = instance.web.py_eval(column.options || '{}');
//                     if (_.isUndefined(options.selection)) {
//                         notify.notify('错误', '需要在字段的options中定义selection属性')
//                         return;
//                     }
//
//                     var index = _.indexOf(options.selection, field_value);
//                     if (index === -1) {
//                         notify.notify('错误', '当前字段的值没有在options中selection属性定义')
//                         return;
//                     }
//                     index += 1;
//                     if (index === options.selection.length) {
//                         index = 0;
//                     };
//
//                     var next_value = options.selection[index];
//
//                     res = {}
//                     res[field_name] = next_value;
//                     model.call('write', [parseInt(data_id), res]).then(function(result) {
//                         current.data('value', next_value);
//                         current.attr('data-value', next_value);
//                         var select = _.find(column.selection, function(select) { return select[0] === next_value})
//                         current.text(select[1]);
//                     })
//                 }).delegate('span.boolean-clickable-mode', 'click', function(e) {
//                     e.stopPropagation();
//                     var current = $(this),
//                         notify = instance.web.notification,
//                         data_id = current.closest('tr').data('id'),
//                         field_name = current.closest('td').data('field'),
//                         field_value = !current.data('value'),
//                         field_text = field_value? '已启用' : '已禁止',
//                         model = new instance.web.Model(self.dataset.model);
//
//                     var column = _.find(self.columns, function(column) { return column.id === field_name})
//                     if (_.isUndefined(column)) {
//                         notify.notify('抱歉', '当前列表中没有定义当前字段');
//                         return;
//                     }
//
//                     res = {}
//                     res[field_name] = field_value;
//                     model.call('write', [parseInt(data_id), res]).then(function(result) {
//                         current.data('value', field_value);
//                         current.attr('data-value', field_value);
//                         current.text(field_text);
//                     });
//                 });
//             return result;
//         },
//     });
//
//     instance.warehouse.selectionClickable = openerp.web.list.Column.extend({});
//     instance.web.list.columns.add('field.selection_clickable', 'instance.warehouse.selectionClickable');
//
//     instance.warehouse.booleanClickable = openerp.web.list.Column.extend({});
//     instance.web.list.columns.add('field.boolean_clickable', 'instance.warehouse.booleanClickable');
// };
