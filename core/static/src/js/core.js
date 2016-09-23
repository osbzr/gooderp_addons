openerp.core = function(instance) {
    instance.web.FormView.include({
        autofocus: function() {
            this._super.apply(this, arguments);
            if (this.get("actual_mode") !== "view" && !this.options.disable_autofocus) {
                if (this.default_focus_button) {
                    this.default_focus_button.$el.focus();
                }
            }
        },

    })
};
