odoo.define('web.float_limit', function(require) {
    var form_widgets = require('web.form_widgets');
    var form_view = require('web.FormView');
    var core = require('web.core');
    
    var float_limit = form_widgets.FieldFloat.extend({
        is_valid: function() {
            res = this._super.apply(this, arguments);
            if (res && this.view && this.view.fields && !_.isUndefined(this.view.fields[this.options.field])) {
                var max_float = this.view.fields[this.options.field].get_value();
                if (max_float > 0 && parseFloat(this.$('input:first').val()) > max_float) {
                    this.view.float_limit_desc = '当前数量已经超出了最大规定数量' + max_float;
                    return false;
                }
            }

            return res
        }
    });
    
    core.form_widget_registry.add('float_limit', float_limit);
    
    form_view.include({
        on_invalid: function() {
            if (this.float_limit_desc) {
                this.do_warn('错误', this.float_limit_desc);
            } else {
                this._super.apply(this, arguments);
            }
        },
    })
});