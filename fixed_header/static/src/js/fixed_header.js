odoo.define('gooderp.fixed_header', function(require) {
    var ListView = require('web.ListView');
       /* 固定表头 */
    ListView.include({
        load_list: function () {
            var self = this;
            this._super.apply(this, arguments);
            var one2many_length = self.$el.parents('.o_form_field_one2many').length;
            if (one2many_length == 0) {
                self.$el.find('table.o_list_view').each(function () {
                    $(this).floatThead({
                        position: 'auto',
                        /*Valid values: 'auto', 'fixed', 'absolute'.
                         Position the floated header using absolute or fixed
                         positioning mode (auto picks best for your table scrolling type).
                         Try switching modes if you encounter layout problems.*/

                        zIndex: 5,  //设置float的优先级 保证不会挡住 其他弹出层  default 1001	z-index of the floating header
                    });
                    $(this).floatThead("reflow");
                });
            }
            return $.when();
        },
    })
});