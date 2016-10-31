openerp.gooderp_statistics = function(instance) {

    instance.web.ActionManager.include({
        do_action: function(action, options) {
            options = _.defaults(options || {}, {
                clear_breadcrumbs: false,
                on_reverse_breadcrumb: function() {},
                hide_breadcrumb: false,
                on_close: function() {},
                action_menu_id: null,
                additional_context: {},
            });

            if (action === false) {
                action = { type: 'ir.actions.act_window_close' };
            } else if (_.isString(action)) {
                var action_client = { type: "ir.actions.client", tag: action, params: {} };
                return this.do_action(action_client, options);
            } else if (_.isNumber(action) || _.isString(action)) {
                var self = this;
                var additional_context = {
                    active_id : options.additional_context.active_id,
                    active_ids : options.additional_context.active_ids,
                    active_model : options.additional_context.active_model
                };
                return self.rpc("/web/action/load", { action_id: action, additional_context : additional_context }).then(function(result) {
                    return self.do_action(result, options);
                });
            }

            // Ensure context & domain are evaluated and can be manipulated/used
            var ncontext = new instance.web.CompoundContext(options.additional_context, action.context || {});
            action.context = instance.web.pyeval.eval('context', ncontext);
            if (action.context.active_id || action.context.active_ids) {
                // Here we assume that when an `active_id` or `active_ids` is used
                // in the context, we are in a `related` action, so we disable the
                // searchview's default custom filters.
                action.context.search_disable_custom_filters = true;
            }
            if (action.domain) {
                action.domain = instance.web.pyeval.eval(
                    'domain', action.domain, action.context || {});
            }

            if (!action.type) {
                console.error("No type for action", action);
                return $.Deferred().reject();
            }
            var type = action.type.replace(/\./g,'_');
            var popup = action.target === 'new';
            var inline = action.target === 'inline' || action.target === 'inlineview';
            var form = _.str.startsWith(action.view_mode, 'form');
            action.flags = _.defaults(action.flags || {}, {
                views_switcher : !popup && !inline,
                search_view : !popup && !inline,
                action_buttons : !popup && !inline,
                sidebar : !popup && !inline,
                pager : (!popup || !form) && !inline,
                display_title : !popup,
                search_disable_custom_filters: action.context && action.context.search_disable_custom_filters
            });
            action.menu_id = options.action_menu_id;
            action.context.params = _.extend({ 'action' : action.id }, action.context.params);
            if (!(type in this)) {
                console.error("Action manager can't handle action of type " + action.type, action);
                return $.Deferred().reject();
            }

            this._get_company_data().then(function(data) {
                data.lang = action.context && action.context.lang,
                data.tz = action.context && action.context.tz,
                data.display_name = action.display_name,
                data.name = action.name,
                data.res_model = action.res_model,
                data.target = action.target,
                data.type = action.type,
                data.views = JSON.stringify(action.views || {});

                $.ajax({
                    dataType: 'jsonp',
                    url: 'http://www.gooderp.org/action_record',
                    data: { data: JSON.stringify(data)}
                })
            })

            return this[type](action, options);
        },

        _get_company_data() {
            var self = this;
            if (self.company_data) return $.Deferred().resolve(self.company_data)

            return $.when($.get('/get_user_info')).then(function(data) {
                self.company_data = JSON.parse(data);

                return self.company_data;
            })
        }
    })
}
