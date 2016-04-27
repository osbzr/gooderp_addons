openerp.finance = function(session) {
    var _t = session.web._t;
    var has_action_id = false;
    var instance = openerp;
    var QWeb = instance.web.qweb; 
    



    instance.web.ListView.List .include({

        render_cell: function (record, column) {
            this._super.apply(this, arguments);
            /*console.log(column,"---");*/
            if (column.widget== 'report_parameter'){
               /*new instance.web.Model("create.balance.sheet.wizard").call("compute_beginning_balance",[]).then(function(result){})*/
                           /* new instance.web.DataSet(this.view, column.relation)
                        .name_get([value]).done(function (names) {
                    if (!names.length) { return; }
                    record.set(column.id, names[0]);
                });*/
            }
            return column.format(record.toForm().data, {
            model: this.dataset.model,
            id: record.get('id')
        });
        }
    });

    instance.finance.report_parameter = instance.web.list.Column.extend({
    });
    instance.web.list.columns.add('field.report_parameter', 'instance.finance.report_parameter');
}
