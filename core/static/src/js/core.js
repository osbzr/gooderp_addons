odoo.define('core.core', function (require) {
    "use strict";
    var ListView = require('web.ListView');
    var common = require('web.list_common');
    var form_relational = require('web.form_relational');
    var data = require('web.data');
    var UserMenu = require('web.UserMenu');
    var session = require('web.session');
    var Model = require('web.Model');
    var FormView = require('web.FormView');
    var WebClient = require('web.AbstractWebClient');
    /*
    One2many字段增加复制按钮
    */
    ListView.List.include({
        /* 绑定事件，监控复制按钮被点击 */
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
            if (this.records.length >= count ||
                _(this.columns).any(function (column) { return column.meta; })) {
                return;
            }
            /* 增加复制按钮 */
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
                    console.log(recored);
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

    /*
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
    //在页面的 表头部分 添加公司图标 及公司名称
    UserMenu.include({
          do_update: function () {
            var self =this;
            this._super.apply(this, arguments);
            var $company_avatar = this.$('.oe_top_company_bar_avatar');
            if (!session.uid) {
                $company_avatar.attr('src', $company_avatar.data('default-src'));
                return $.when();
            }
            new Model("res.company").call("read", [session.company_id]).then(function(data) {
                self.$('.oe_topbar_company_name').text(data[0]['display_name']);
            })
            var company_avatar_src = session.url('/web/image', {model:'res.company', field: 'logo', id:session.company_id});
            $company_avatar.attr('src', company_avatar_src);
        },
    });
    /*把设置默认值的的按钮菜单 放到form菜单的更多里面。
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
    //頁面title 換成自己定義的字符！
    WebClient.include({
         init: function(parent) {
                this._super(parent);
                this.set('title_part', {"zopenerp": "GoodERP"});
         },
        set_title_part: function(part, title) {
            var tmp = _.clone(this.get("title_part"));
            tmp[part] = title;
            if ('zopenerp' in tmp){
                tmp['zopenerp'] = 'GoodERP';
            }
            this.set("title_part", tmp);
        },
      });
})
