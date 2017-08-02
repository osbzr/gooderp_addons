odoo.define('web.delete_select', function(require) {

var core = require('web.core');
var session = require('web.session');
var formats = require('web.formats');
var QWeb = core.qweb;
var ListView = require('web.ListView');
var form_relational = require('web.form_relational');
var form_widget_registry = core.form_widget_registry;

   /* 固定表头 */
ListView.include({

    load_list: function () {
        var self = this;
        return this._super.apply(this, arguments).done(function () {
            self.$("[name='delete_select']").click(function() {
                self.do_delete_selected();
            });
        });
    },
});


form_widget_registry.get('one2many').include({
    //multi_selection = true,
    init: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.multi_selection = true;
    },
});

//core.form_widget_registry
//    .add('delete_select', one2many_delete_select);

});