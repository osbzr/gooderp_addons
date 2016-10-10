odoo.define('core.core', function (require) {
"use strict";
var ListView = require('web.ListView');
var FormView = require('web.FormView');
var common = require('web.list_common');
var form_relational = require('web.form_relational');
var data = require('web.data');
FormView.include({
    autofocus: function () {
        this._super.apply(this, arguments);
        if (this.get("actual_mode") !== "view" && !this.options.disable_autofocus) {
            if (this.default_focus_button) {
                this.default_focus_button.$el.focus();
            }
        }
    },

});

ListView.List.include({
    init: function () {
        this._super.apply(this, arguments);
        var self = this;
        self.$current = self.$current.delegate('td.oe_list_record_copy', 'click', function (e){
            e.stopPropagation();
            var $target = $(e.target),
                $row = $target.closest('tr'),
                record_id = self.row_id($row),
                record = self.records.get(record_id);
            self.view.do_copy_record(record);
        });
    },
     pad_table_to: function (count) {
        if (this.records.length >= count ||
                _(this.columns).any(function(column) { return column.meta; })) {
            return;
        }
        var cells = [];
        if (this.options.deletable) {
            cells.push('<td class="copy_record"></td>');
        }
        if (this.options.selectable) {
            cells.push('<td class="o_list_record_selector"></td>');
        }
        _(this.columns).each(function(column) {
            if (column.invisible === '1') {
                return;
            }
            cells.push('<td title="' + column.string + '">&nbsp;</td>');
        });
        if (this.options.deletable) {
            cells.push('<td class="o_list_record_delete"></td>');
        }
        cells.unshift('<tr>');
        cells.push('</tr>');

        var row = cells.join('');
        this.$current
            .children('tr:not([data-id])').remove().end()
            .append(new Array(count - this.records.length + 1).join(row));
    },
});
ListView.include({
     make_empty_record_copy: function (copy_recored) {
        var attrs = {id: false};
        _(this.columns).chain()
            .filter(function (x) { return x.tag === 'field'; })
            .pluck('name')
            .each(function (field) { attrs[field] = copy_recored[field]; });
        return new common.Record(attrs);
    },
     do_add_record: function () {
         var self =this;
         if (self.copy_recored===undefined) {
             this._super.apply(this, arguments);
         }else{
              if (this.editable()) {
                 this.$('table:first').show();
                 this.$('.oe_view_nocontent').remove();
                 var recored = this.make_empty_record_copy(self.copy_recored.attributes);
                  this.records.add(recored, {at: (this.prepends_on_create())? 0 : null});
                  console.log(recored);
                 this.start_edition(recored,undefined);
             } else {
                 this._super.apply(this, arguments);
             }
         }
     },
    do_copy_record: function (record) {
        var self = this;
        var def = self.save_edition();
        self.copy_recored=record;
        $.when(def).done(self.do_add_record.bind(self.x2m));
        self.copy_recored =undefined;
    }
});
form_relational.X2ManyList.include({
    pad_table_to: function (count) {
        if (!this.view.is_action_enabled('create') || this.view.x2m.get('effective_readonly')) {
            this._super(count);
            return;
        }
        this._super(count > 0 ? count - 1 : 0);
        var self = this;
        var columns = _(this.columns).filter(function (column) {
            return column.invisible !== '1';
        }).length;
        if (this.options.selectable) { columns++; }
        if (this.options.deletable) { columns++;}
        columns++;
        var $cell = $('<td>', {
            colspan: columns,
            'class': 'o_form_field_x2many_list_row_add'
        }).append(
            $('<a>', {href: '#'}).text(_t("Add an item"))
                .click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var def;
                    console.log('++',self.view.editable())
                    if (self.view.editable()) {
                        // FIXME: there should also be an API for that one
                        if (self.view.editor.form.__blur_timeout) {
                            clearTimeout(self.view.editor.form.__blur_timeout);
                            self.view.editor.form.__blur_timeout = false;
                        }
                        def = self.view.save_edition();
                    }
                    $.when(def).done(self.view.do_add_record.bind(self));
                }));
        var $padding = this.$current.find('tr:not([data-id]):first');
        var $newrow = $('<tr>').append($cell);
        if ($padding.length) {
            $padding.before($newrow);
        } else {
            this.$current.append($newrow);
        }
    },
});
})