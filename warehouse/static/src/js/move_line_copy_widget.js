openerp.warehouse = function(instance) {
	var QWeb = instance.web.qweb,
        _t = instance.web._t;
        
    instance.web.warehouse = instance.web.warehouse || {};
    
    instance.web.form.One2ManyListView = instance.web.form.One2ManyListView.extend({
        do_copy_record: function (record) {
            var self = this;
            if (record) {
                self.$el.find('warehouse.wh_in_form:first').show();
                self.$el.find('.oe_view_nocontent').remove();
                var new_record_id =_.uniqueId(self.dataset.virtual_id_prefix); 
                var new_record = self.make_empty_record(false);
                new_record.attributes = _.clone(record.attributes);
                new_record.attributes.id = new_record_id;
                var data = _.clone(new_record.attributes), options = {};
                delete data.id;
                _.each(data, function(value, name) {
                    if (value instanceof Array &&  (value.length == 2) &&  value[0] && value[1]){
                        data[name] = value[0];
                    }
                });
                var cached = {
                    id: new_record_id,
                    values: _.extend({}, data, (options || {}).readonly_fields || {}),
                    defaults:{}
                };
                self.dataset.to_create.push(_.extend(_.clone(cached), {values: _.clone(data)}));
                self.dataset.cache.push(cached);
                self.dataset.remove_ids([new_record_id]);
                self.records.add(new_record, {at: self.records.length});
                // set edit state
                //self.start_edition(new_record);
                self.$el.find('[data-id=' + new_record_id + ']').click();
            }
        },
    });

    instance.web.ListView.List.include({
        init: function () {
            this._super.apply(this, arguments);
            var self = this;
            self.$current = self.$current.delegate('td.oe_list_record_copy button', 'click', function (e) {
                e.stopPropagation();
                var $target = $(e.target), 
                    $row = $target.closest('tr'), 
                    record_id = self.row_id($row),
                    record = self.records.get(record_id);
                self.view.do_copy_record(record);
            });
        },
    });
};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax: