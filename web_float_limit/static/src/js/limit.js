openerp.web_float_limit = function(instance) {
    instance.web.form.widgets = instance.web.form.widgets.extend({
        'float_limit' : 'instance.web.form.FieldFloatLimit',
    });

    instance.web.form.FieldFloatLimit = instance.web.form.FieldFloat.extend({
        is_valid: function() {
            res = this._super.apply(this, arguments);
            var notify = instance.web.notification;
            if (res && this.view && this.view.fields && !_.isUndefined(this.view.fields[this.options.field])) {
                var max_float = this.view.fields[this.options.field].get_value();
                console.warn('max_float', max_float);
                if (max_float > 0 && parseFloat(this.$('input:first').val()) > max_float) {
                    this.view.float_limit_desc = '当前数量已经超出了最大规定数量' + max_float;
                    return false;
                }
            }

            return res
        }
    })

    instance.web.FormView.include({
        on_invalid: function() {
            if (this.float_limit_desc) {
                this.do_warn('错误', this.float_limit_desc);
            } else {
                this._super.apply(this, arguments);
            }
        },
    })

};