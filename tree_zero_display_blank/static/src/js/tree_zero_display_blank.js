odoo.define('web.tree_zero_display_blank', function(require) {
    var list_view = require('web.ListView');
    
    list_view.Column.include({
        _format: function(row_data, options) {
            if (!isNaN((row_data[this.id]['value']))  && !parseFloat(row_data[this.id]['value'])) {
                return '';
            }
            return this._super.apply(this, arguments);
        }
    });
});