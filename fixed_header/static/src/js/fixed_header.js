odoo.define('gooderp.fixed_header', function(require) {
    var ListView = require('web.ListView');
       /* 固定表头 */
    ListView.include({
        load_list: function () {
            var self = this;
            return this._super.apply(this, arguments).done(function () {
                var form_field_length = self.$el.parents('.o_form_field').length;
                var scrollArea = $(".o_content")[0];
                function do_freeze () {
                    self.$el.find('table.o_list_view').each(function () {
                        $(this).stickyTableHeaders({scrollableArea: scrollArea});
                    });
                }

                if (form_field_length == 0) {
                    do_freeze();
                    $(window).unbind('resize', do_freeze).bind('resize', do_freeze);
                }
            });
        },
    });

    ListView.Groups.include({
        render_groups: function () {
            var self = this;
            var placeholder = this._super.apply(this, arguments);
            var grouping_freezer = document.createElement("script");

            grouping_freezer.innerText = "$('.o_group_header').click(function () { setTimeout('" +
                "var scrollArea = $(\".o_content\")[0]; " +
                "$(\"table.o_list_view\").each(function () { $(this).stickyTableHeaders({scrollableArea: scrollArea}); }); " +
                "',250); })";

            placeholder.appendChild(grouping_freezer);
            return placeholder;
        },
    });

});