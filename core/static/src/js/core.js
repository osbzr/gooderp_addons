odoo.define('core.core', function (require) {
    "use strict";
    var ListView = require('web.ListView');
    var common = require('web.list_common');
    var form_relational = require('web.form_relational');
    var data = require('web.data');
    var UserMenu = require('web.UserMenu');
    var Menu = require('web.Menu');
    var session = require('web.session');
    var Model = require('web.Model');
    var FormView = require('web.FormView');
    var PivotView = require('web.PivotView');
    var WebClient = require('web.AbstractWebClient');
    var formats = require('web.formats');
    var data_manager = require('web.data_manager');
    var core = require('web.core');
    var _t = core._t;
    var FieldBinaryFile = core.form_widget_registry.get('binary');
    var utils = require('web.utils');
    /*
    One2many字段增加复制按钮
    */
    ListView.List.include({
        /** 绑定事件，监控复制按钮被点击 */
        init: function () {
            this._super.apply(this, arguments);
            var self = this;
            self.$current = self.$current.delegate('td.oe_list_record_copy', 'click', function (e) {
                e.stopPropagation();
                var $target = $(e.target),
                    $row = $target.closest('tr'),
                    record_id = self.row_id($row),
                    record = self.records.get(record_id);
                self.view.do_copy_record(record);
            });
        },
        pad_table_to: function (count) {
            count -=3;    /* 表格预留空行太多很难看 */
            if (this.records.length >= count ||
                _(this.columns).any(function (column) { return column.meta; })) {
                return;
            }
            /** 增加复制按钮 */
            var cells = [];
            if (this.options.deletable) {
                cells.push('<td class="copy_record"></td>');
            }
            if (this.options.selectable) {
                cells.push('<td class="o_list_record_selector"></td>');
            }
            _(this.columns).each(function (column) {
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
        /** 在form中的tree列表行上前添加复制的按钮 以方便创建相同的行 */
        make_empty_record_copy: function (copy_recored) {
            var attrs = { id: false };
            _(this.columns).chain()
                .filter(function (x) { return x.tag === 'field'; })
                .pluck('name')
                .each(function (field) { attrs[field] = copy_recored[field]; });
            return new common.Record(attrs);
        },
        do_add_record: function () {
            var self = this;
            if (self.copy_recored === undefined) {
                this._super.apply(this, arguments);
            } else {
                if (this.editable()) {
                    this.$('table:first').show();
                    this.$('.oe_view_nocontent').remove();
                    var recored = this.make_empty_record_copy(self.copy_recored.attributes);
                    this.records.add(recored, { at: (this.prepends_on_create()) ? 0 : null });
                    this.start_edition(recored, undefined);
                } else {
                    this._super.apply(this, arguments);
                }
            }
        },
        do_copy_record: function (record) {
            var self = this;
            var def = self.save_edition();
            self.copy_recored = record;
            $.when(def).done(self.do_add_record.bind(self.x2m));
            self.copy_recored = undefined;
        }
    });

    /**
    使用 options="{'color':'random'}" 来实现多对多控件标签显示随机颜色
    */
    form_relational.FieldMany2ManyTags.include({
        render_tag: function (data) {
            if (this.options.color && this.options.color == 'random') {
                data = _.each(data, function (data_one, index) {
                    if (!data_one.color) {
                        data_one.color = index % 9 + 1;
                    }
                    return data_one;
                });
            }
            this._super.apply(this, arguments);
        },
    });

    /**
     * 2016-11-15 开阖静静(gilbert@osbzr.com)
     * 把设置默认值的的按钮菜单 放到form菜单的更多里面。
    */
    FormView.include({
       render_sidebar: function($node) {
           this._super.apply(this, arguments);
           if(this.sidebar){
                this.sidebar.add_items('other', _.compact([
                   { label: '设默认值', callback: this.on_click_set_defaults}
                ]));
                this.sidebar.appendTo($node);
                this.toggle_sidebar();
           }
        },
        on_click_set_defaults:function() {
            this.open_defaults_dialog();
        },
    });
    /**2016-11-23  开阖静静(gilbert@osbzr.com)
    * pivot 视图改造 (在pivot 视图中 特殊颜色 标示满足条件的字段) 只需要在对应的字段上例如
    *<field name="goods_qty" type="measure" pivot_color="{'color':'blue','greater_than_field':'cost'}"/>
    *<field name="goods_uos_qty" type="measure"   pivot_color="{'color':'blue','greater_than':15 }"/>
    * 表示  name="goods_qty" 或 name="goods_uos_qty" 大于 greater_than常量的 值或者 大于 greater_than_field 显示的值
    * greater_than 为对比的字段  类型为float 是个常量
    * greater_than_field 为字段name 是变量
    * greater_than 和 greater_than_field 同时存在,以greater_than_field为优先
    *2016-12-16  开阖静静(gilbert@osbzr.com)
    *  pivot 视图中某些字段加了权限组字段 但是不起作用 没在相应权限组里面的人任然能够看到对应的字段
    *  bug 造成原因 : 系统原生代码里面没有处理这部分的功能 在取数据的时候取出了所有的可以用来显示的数据
    *  但是系统后台是对前端的数据经过处理的 如果不让看到的字段 会有invisible='1' 和 modifiers:{'invisible':true}
    *  所以可以根据这点差异进行必要数据处理
     *   willstart 有个坑.....willstart 中的代码总会执行..
    * */

    PivotView.include({
         init: function() {
             this.pivot_color = [];
             this.invisible_field = [];
             this._super.apply(this, arguments);
         },
         willStart: function () {
             var self = this;
             self.pivot_color_field = [];

             this.fields_view.arch.children.forEach(function (field) {
                  if(field.attrs.invisible==='1') {
                    self.invisible_field.push(field.attrs.name);
                  }
                 if (field.attrs && field.attrs.pivot_color!=undefined){
                    self.pivot_color_field.push(field.attrs.name);
                    var pivot_color_obj =py.eval(field.attrs.pivot_color);
                    self.pivot_color.push(pivot_color_obj);
                 }
            });
            return this._super.apply(this, arguments);;
        },

        prepare_fields: function (fields) {
            var self = this,
                groupable_types = ['many2one', 'char', 'boolean',
                                   'selection', 'date', 'datetime'];
            this.fields = fields;
            _.each(fields, function (field, name) {
                if ((name !== 'id') && (field.store === true) && self.invisible_field.indexOf(name)<0) {
                    // 不在要隐藏的字段的列表里面
                    if ((field.type === 'integer' || field.type === 'float' || field.type === 'monetary')) {
                        self.measures[name] = field;
                    }
                    if (_.contains(groupable_types, field.type)) {
                        self.groupable_fields[name] = field;
                    }
                }
            });
            this.measures.__count__ = {string: _t("Count"), type: "integer"};
        },
        start: function () {
            var self = this;
             _.each(self.invisible_field, function (field) {
                 if(self.active_measures.indexOf(field)>=0){
                        self.active_measures.splice(self.active_measures.indexOf(field)
                                                   ,self.active_measures.indexOf(field));}
                 if(self.measures[field]!==undefined){delete self.measures[field]}
             });
             this._super.apply(this, arguments);
        },
        change_color: function (rows, $cell, i, j, nbr_measures,field_index) {
            var compare_flag = true,
                greater_than_field = this.pivot_color[field_index].greater_than_field,
                greater_than = this.pivot_color[field_index].greater_than;

            if (!(greater_than_field == "" || greater_than_field == undefined || greater_than_field == null)
                && this.active_measures.indexOf(greater_than_field)>=0){
                compare_flag = rows[i].values[j] > rows[i].values[this.active_measures.indexOf(greater_than_field)
                    + Math.floor(j / nbr_measures) * nbr_measures]
            }else if(!(greater_than == "" || greater_than == undefined || greater_than == null)){
                compare_flag = rows[i].values[j] >greater_than
            }
            if (compare_flag) {
                $cell.css('color', this.pivot_color[field_index].color|| 'black');
            }else if( this.pivot_color[field_index].default_color){
                 $cell.css('color', this.pivot_color[field_index].default_color || 'black');
            }
        },
        draw_rows: function ($tbody, rows) {
            var self = this,
                i, j, value, $row, $cell, $header,
                nbr_measures = this.active_measures.length,
                length = rows[0].values.length,
                display_total = this.main_col.width > 1;

            var groupby_labels = _.map(this.main_row.groupbys, function (gb) {
                return self.fields[gb.split(':')[0]].string;
            });
            var measure_types = this.active_measures.map(function (name) {
                return self.measures[name].type;
            });
            var widgets = this.widgets;
            for (i = 0; i < rows.length; i++) {
                $row = $('<tr>');
                $header = $('<td>')
                    .text(rows[i].title)
                    .data('id', rows[i].id)
                    .css('padding-left', (5 + rows[i].indent * 30) + 'px')
                    .addClass(rows[i].expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');
                if (rows[i].indent > 0) $header.attr('title', groupby_labels[rows[i].indent - 1]);
                $header.appendTo($row);
                for (j = 0; j < length; j++) {

                    value = formats.format_value(rows[i].values[j], {
                        type: measure_types[j % nbr_measures],
                        widget: widgets[j % nbr_measures]
                    });
                    $cell = $('<td>')
                        .data('id', rows[i].id)
                        .data('col_id', rows[i].col_ids[Math.floor(j / nbr_measures)])
                        .toggleClass('o_empty', !value)
                        .text(value)
                        .addClass('o_pivot_cell_value text-right');
                    if (((j >= length - this.active_measures.length) && display_total) || i === 0) {
                        $cell.css('font-weight', 'bold');
                    }
                    if(this.pivot_color_field.indexOf(this.active_measures[j % nbr_measures])>=0){
                        var field_index = this.pivot_color_field.indexOf(this.active_measures[j % nbr_measures])
                        this.change_color(rows, $cell, i, j, nbr_measures,field_index);
                    }
                    $row.append($cell);
                    $cell.toggleClass('hidden-xs', j < length - this.active_measures.length);
                }
                $tbody.append($row);
            }
        },

    });
    /** 2016-11-30  开阖静静(gilbert@osbzr.com)
    *
    * 鼠标悬停即展开(二级菜单) --前提是在backend_theme
     * 主题下| 在没有安装主题的场景下并没有测试  */
    Menu.include({
        events: {
            mouseenter: "on_open_second_menu",
            mouseleave: "on_close_second_menu",
        },

        on_open_second_menu: function (e) {
            var $target = $(e.target);
            $target.parent().addClass('open');
            if($target.attr('aria-expanded')!=undefined && !$target.attr('aria-expanded')){
                $target.attr('aria-expanded', true);
            };
            var menu_list = $target.parent().find('.oe_secondary_submenu');
            menu_list.show();
        },
        on_close_second_menu: function (e) {
            var $target = $(e.target);
            $target.parent().removeClass('open');
            var menu_list = $target.parent().find('.oe_secondary_submenu');
            var dropdown_a = $target.parent().find('.dropdown-toggle')
            if(dropdown_a.attr('aria-expanded')!=undefined && $target.attr('aria-expanded')){
                $target.attr('aria-expanded', false);
            };
            menu_list.hide();
        },
        bind_menu: function () {
            this._super.apply(this, arguments);
            this.$second_menu = this.$el.parents().find('.dropdown-toggle');
            this.$second_menu.on('mouseenter', this.on_open_second_menu.bind(this));
            this.$second_menu.parent().on('mouseleave', this.on_close_second_menu.bind(this));
        }

    });
    /************************************************************
     *2017-01-10  开阖静静(gilbert@osbzr.com)
     * 实现在form页面上的 one2many字段 子字段的必输报错的详细提示
     *对js基础方法的理解不是很深刻，难免用的不是很恰当，有比较好的实现再去修改，
     * ***********************************************************/
    FormView.include({
         on_invalid: function() {
            var warnings = _(this.fields).chain()
                .filter(function (f) {return !f.is_valid(); })
                .map(function (f) {
                    var  field_list = ''
                    if((f.field.type=='one2many' || f.field.type=='many2many')){
                        var list =_.map(f.views[0].fields_view.fields,function (value, key_vals) {
                            if(value.required ||(value.__attrs && value.__attrs.required==='1')){
                                return [key_vals,value.string]}
                        }).filter(function(value){if(value){return value}});
                        var dict_list = f.dataset.cache;
                        var list_keys = _.map(list,function (value) {return value[0]});
                        var list_vals = _.map(list,function (value) {return value[1]});
                        if(dict_list) {
                            var index = 0;
                            var break_flag = false;
                            field_list = _.map(dict_list, function (value,key) {
                                index= index+1;
                                if(break_flag){return undefined}else{
                                    var field_list_message = _.map(value.values,function (field,field_name) {
                                        if(field===false &&list_keys.indexOf(field_name)>=0){return field_name
                                     }else{return undefined}}).filter(function(value){return value});
                                    if(_.any(field_list_message)){
                                     break_flag = true
                                     return "   <li>第"+(index)+"行 "+ list_vals[list_keys.indexOf(field_list_message[0])]+"</li>";}
                                }
                           }).filter(function(value){if(value){return value}});
                        }
                    }
                    return _.str.sprintf('<li>%s</li>',_.escape(f.string)+field_list);
                }).value();
            warnings.unshift('<ul>');
            warnings.push('</ul>');
            this.do_warn(_t("The following fields are invalid:"), warnings.join(''));
         },
    });
// realize pdf view function.
var FieldPdfViewer = FieldBinaryFile.extend({
    template: 'FieldPdfViewer',
    init: function(){
        this._super.apply(this, arguments);
        this.PDFViewerApplication = false;
    },
    get_uri: function(){
        var query_obj = {
            model: this.view.dataset.model,
            field: this.name,
            id: this.view.datarecord.id
        };
        var query_string = $.param(query_obj);
        var url = encodeURIComponent('/web/image?' + query_string);
        var viewer_url = '/web/static/lib/pdfjs/web/viewer.html?file=';
        return viewer_url + url;
    },
    on_file_change: function(ev) {
        this._super.apply(this, arguments);
        if(this.PDFViewerApplication){
            var files = ev.target.files;
            if (!files || files.length === 0) {
              return;
            }
            var file = files[0];
            // TOCheck: is there requirement to fallback on FileReader if browser don't support URL
            this.PDFViewerApplication.open(URL.createObjectURL(file), 0);
        }
    },
    render_value: function() {
        var $pdf_viewer = this.$('.o_form_pdf_controls').children().add(this.$('.o_pdfview_iframe')),
            $select_upload_el = this.$('.o_select_file_button').first(),
            $iFrame = this.$('.o_pdfview_iframe'),
            value = this.get('value'),
            self = this;

        var bin_size = utils.is_bin_size(value);
        $iFrame.on('load', function(){
            self.PDFViewerApplication = this.contentWindow.window.PDFViewerApplication;
            self.disable_buttons(this);
        });
        if (this.get("effective_readonly")) {
            if (value) {
                this.$el.off('click'); // off click event(on_save_as) of FieldBinaryFile
                $iFrame.attr('src', this.get_uri());
            }
        } else {
            if (value) {
                $pdf_viewer.removeClass('o_hidden');
                $select_upload_el.addClass('o_hidden');
                if(bin_size){
                    $iFrame.attr('src', this.get_uri());
                }
            } else {
                $pdf_viewer.addClass('o_hidden');
                $select_upload_el.removeClass('o_hidden');
            }
        }
    },
    disable_buttons: function(iframe){
        if (this.get("effective_readonly")){
            $(iframe).contents().find('button#download').hide();
        }
        $(iframe).contents().find('button#openFile').hide();
    }

});
core.form_widget_registry.add('pdf_viewer', FieldPdfViewer);
});
