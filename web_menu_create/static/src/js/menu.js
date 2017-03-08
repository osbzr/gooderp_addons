odoo.define('web.menu_create', function(require) {
    var Menu = require('web.Menu');
    var Model = require('web.DataModel');
    
    Menu.include({
        init: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.on('menu_bound', this, function() {
                var $all_menus = self.$el.parents('.o_web_client').find('.o_sub_menu').find('[data-menu]');
                var all_menu_ids = _.map($all_menus, function (menu) {return parseInt($(menu).attr('data-menu'), 10);});
                this.do_load_create_tag(all_menu_ids);
            });
        },
        do_load_create_tag: function(menu_ids) {
            var self = this;
            menu_ids = _.compact(menu_ids);
            if (_.isEmpty(menu_ids)) {
                return $.when();
            }

            return new Model('ir.ui.menu').call('load_create_tag', [menu_ids]).then(function(result) {
                _.each(result, function(menu_id) {
                    var $item = self.$secondary_menus.find('a[data-menu="' + menu_id + '"]');
                    $item.append("<span class='menu-create-tag'>新建</span>");
                });

                self.$secondary_menus.find('span.menu-create-tag').click(function(e) {
                    var current = $(this),
                        action_id = $(this).closest('a').data('action-id'),
                        menu_id = $(this).closest('a').data('menu');

                    if (action_id) {
                        e.preventDefault();
                        e.stopPropagation();

                        self.open_menu(menu_id);
                        self.on_create_tag_action(action_id);
                    }
                })
            });
        },
        on_create_tag_action: function(action_id) {
            var self = this,
                parent = this.__parentedParent;

            return parent.menu_dm.add(parent.rpc("/web/action/load", { action_id: action_id }))
                .then(function (result) {
                    result.view_mode = 'form';
                    var form_views = _.find(result.views, function(view) { return view[1] == 'form'})
                    result.views = (_.isUndefined(form_views))? [[false, 'form']] : [form_views];

                    return parent.action_mutex.exec(function() {
                        var completed = $.Deferred();
                        $.when(parent.action_manager.do_action(result, {
                            clear_breadcrumbs: true,
                            action_menu_id: parent.menu.current_menu,
                        })).always(function() {
                            completed.resolve();
                        });
                        setTimeout(function() {
                            completed.resolve();
                        }, 2000);
                        return completed;
                    });
                });
        },
    }); 
});