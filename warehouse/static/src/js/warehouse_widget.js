openerp.warehouse = function(instance) {
    instance.web.list.Column.include({
        _format: function(row_data, options) {
            if (this.widget === 'selection_clickable' && !_.isUndefined(this.selection)) {
                var field_name = row_data[this.id]['value'],
                    select = _.find(this.selection, function(select) { return select[0] === field_name})

                if (_.isUndefined(select)) {
                    delete this.widget;
                    return this._super(row_data, options)
                }
                return _.str.sprintf("<span class='selection-clickable-mode' data-value=%s >%s</span>",
                    select[0], select[1]);
            } else if (this.widget === 'boolean_clickable') {
                console.warn('boolean_clickable', row_data, this);

                return _.str.sprintf("<span class='boolean-clickable-mode' data-value=%s>%s</span>",
                    row_data[this.id]['value'],
                    row_data[this.id]['value']? '已启用' : '已禁止');

            } else {
                return this._super(row_data, options);
            };

        },
    });

    instance.web.ListView.List.include({
        render: function() {
            var self = this;
                result = this._super(this, arguments),

            this.$current.delegate('span.selection-clickable-mode', 'click', function(e) {
                    e.stopPropagation();
                    var current = $(this),
                        notify = instance.web.notification,
                        data_id = current.closest('tr').data('id'),
                        field_name = current.closest('td').data('field'),
                        field_value = current.data('value'),
                        model = new instance.web.Model(self.dataset.model);

                    var column = _.find(self.columns, function(column) { return column.id === field_name})
                    if (_.isUndefined(column)) {
                        notify.notify('抱歉', '当前列表中没有定义当前字段');
                        return;
                    }

                    var options = instance.web.py_eval(column.options || '{}');
                    if (_.isUndefined(options.selection)) {
                        notify.notify('错误', '需要在字段的options中定义selection属性')
                        return;
                    }

                    var index = _.indexOf(options.selection, field_value);
                    if (index === -1) {
                        notify.notify('错误', '当前字段的值没有在options中selection属性定义')
                        return;
                    }
                    index += 1;
                    if (index === options.selection.length) {
                        index = 0;
                    };

                    var next_value = options.selection[index];

                    res = {}
                    res[field_name] = next_value;
                    model.call('write', [parseInt(data_id), res]).then(function(result) {
                        current.data('value', next_value);
                        current.attr('data-value', next_value);
                        var select = _.find(column.selection, function(select) { return select[0] === next_value})
                        current.text(select[1]);
                    })
                }).delegate('span.boolean-clickable-mode', 'click', function(e) {
                    e.stopPropagation();
                    var current = $(this),
                        notify = instance.web.notification,
                        data_id = current.closest('tr').data('id'),
                        field_name = current.closest('td').data('field'),
                        field_value = !current.data('value'),
                        field_text = field_value? '已启用' : '已禁止',
                        model = new instance.web.Model(self.dataset.model);

                    var column = _.find(self.columns, function(column) { return column.id === field_name})
                    if (_.isUndefined(column)) {
                        notify.notify('抱歉', '当前列表中没有定义当前字段');
                        return;
                    }

                    res = {}
                    res[field_name] = field_value;
                    model.call('write', [parseInt(data_id), res]).then(function(result) {
                        current.data('value', field_value);
                        current.attr('data-value', field_value);
                        current.text(field_text);
                    });
                });
            return result;
        },
    });

    instance.warehouse.selectionClickable = openerp.web.list.Column.extend({});
    instance.web.list.columns.add('field.selection_clickable', 'instance.warehouse.selectionClickable');

    instance.warehouse.booleanClickable = openerp.web.list.Column.extend({});
    instance.web.list.columns.add('field.boolean_clickable', 'instance.warehouse.booleanClickable');


    instance.web.form.One2ManyListView.include({
        do_copy_record: function (record) {
            var self = this;
            if (record) {
                self.$el.find('table:first').show();
                self.$el.find('.oe_view_nocontent').remove();
                var new_record_id =_.uniqueId(self.dataset.virtual_id_prefix);
                var new_record = self.make_empty_record(false);
                new_record.attributes = _.clone(record.attributes);
                new_record.attributes.lot = '';
                new_record.attributes.goods_qty = 0.0;
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
                // self.start_edition(new_record);
                self.$el.find('[data-id=' + new_record_id + ']').click();
            }
        },
    });

    instance.web.ListView.List.include({
        init: function () {
            this._super.apply(this, arguments);
            var self = this;
            self.$current = self.$current.delegate('td.oe_list_record_copy button', 'click', function (e){
                e.stopPropagation();
                var $target = $(e.target),
                    $row = $target.closest('tr'),
                    record_id = self.row_id($row),
                    record = self.records.get(record_id);
                self.view.do_copy_record(record);
            });
        },
    });
    
    instance.web.FormView.include({
    	load_form: function() {
    		var self = this,
    		    res = this._super.apply(this, arguments);
    		
    		return res.then(function() {
    			self.$el.on('keydown', '.ge_scan_barcode', function(event) {
    				if (event.keyCode === 13){
    					new instance.web.Model("wh.move").call("scan_barcode",[self.model,$(this).val(),self.datarecord.id]).then(
    						function() {
                        		self.reload();
                        		self.$el.find('input').val('');
    						}
    					);
    				}
    			})
    		});
    	},
    });
    
};