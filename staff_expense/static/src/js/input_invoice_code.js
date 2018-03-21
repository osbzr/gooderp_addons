odoo.define('staff_expense.staff_expense', function (require) {
"use strict";
var ListView = require('web.ListView');
var FormView = require('web.FormView');
var form_relational = require('web.form_relational');
var data = require('web.data');
var Model = require('web.Model');
var menu = require('web.Menu');

FormView.include({
    start: function() {
        var self = this,
            res = this._super.apply(this, arguments);

        self.$el.on('keydown', '.do_input_invoice_code', function(event) {
            if (event.keyCode === 13) {
                var $this = $(this);
                return self.save().done(function(result) {
                    self.trigger("save", result);
                    self.reload().then(function() {
                        self.to_view_mode();
                        var menu = menu;
                        if (menu) {
                            menu.do_reload_needaction();
                        }
                    }).then(function() {
                        new Model("hr.expense.line").call("saomiaofapiao",[self.model, $this.val(), self.datarecord.id]).then(
                            function() {
                                self.reload();
                                self.$el.find('input').val('');
                            }
                        );
                    }).then(function() {
                        $this.focus();
                    })
                });
            }
        })
    },
});
})