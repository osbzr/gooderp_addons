openerp.tree_zero_dispaly_blank = function(session) {
    var _t = session.web._t;
    var has_action_id = false;
    var instance = openerp;
    var QWeb = instance.web.qweb; 

    instance.web.list.Column.include({
        _format: function(row_data, options) {
            if (!isNaN((row_data[this.id]['value']))  && !parseFloat(row_data[this.id]['value'])) {
                return '';
            }
            return this._super.apply(this, arguments);
        },
    });
}
