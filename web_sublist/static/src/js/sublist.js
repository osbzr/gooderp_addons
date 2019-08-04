odoo.define('web.sublist', function(require) {
    var list_view = require('web.ListView');
    var pyeval = require('web.pyeval');
    var core = require('web.core');
    var utils = require('web.utils');
    var Model = require('web.DataModel');
    
    var RELATION_TAG = 'RELATION_SUBLIST_MULTI';
    
    var relation_sublist = list_view.Column.extend({
        format: function(row_data, options) {
            var values = row_data[this.id]['value'],
                options = pyeval.py_eval(this.options || '{}'),
                field_value = _.map(_.map(values, function(value) { return value[options.field]; }), function(value) {
                    return _.isArray(value)? value[1]: value;
                });

            // 通过without去除掉undefined的值
            return core.qweb.render('web_sublist.sublist', {'values': _.without(field_value, undefined)}).trim() 
        }
    });

    list_view.Groups.include({
        render_dataset: function (dataset) {
            var self = this,
                list = new (this.view.options.ListType)(this, {
                    options: this.options,
                    columns: this.columns,
                    dataset: dataset,
                    records: this.records
                });
            this.bind_child_events(list);

            var view = this.view;
            var current_min = this.datagroup.openable ? this.current_min : view.current_min;

            var fields = _.pluck(_.select(this.columns, function(x) {return x.tag == "field";}), 'name');
            var options = { offset: current_min - 1, limit: view._limit, context: {bin_size: true} };
            return utils.async_when().then(function() {
                return dataset.read_slice(fields, options).then(function (records) {
                    // FIXME: ignominious hacks, parents (aka form view) should not send two ListView#reload_content concurrently
                    if (self.records.length) {
                        self.records.reset(null, {silent: true});
                    }
                    if (!self.datagroup.openable) {
                        // Update the main list view pager
                        view.update_pager(dataset, current_min);
                    }

                    self.records.add(records, {silent: true});

                    var containers = {}

                    // 统计需要定义子列表的字段
                    _.each(list.columns, function(column) {
                        if (column.widget === 'relation_sublist') {
                            var options = pyeval.py_eval(column.options || '{}');
                            if (_.isUndefined(containers[column.id])) {
                                containers[column.id] = {relation: column.relation, fields: [], ids: []};
                            }

                            containers[column.id]['fields'].push(options.field);
                        }
                    });

                    // 统计需要定义子列表字段的ids
                    self.records.each(function(record) {
                        _.each(_.keys(containers), function(key) {
                            containers[key]['ids'] = containers[key]['ids'].concat(record.get(key));
                        });
                    });

                    var deferreds = [];
                    _.each(_.keys(containers), function(key) {
                        var container = containers[key];
                        deferreds.push(new Model(container.relation).call('read', [container.ids, container.fields]).then(function(results) {
                            return {
                                results: results,
                                key: key,
                            }
                        }))
                    })
                    
                    var RELATION_TAG = 'RELATION_SUBLIST_MULTI';
                    utils.async_when.apply(null, deferreds).then(function() {
                        _.each(arguments, function(item) {
                            var results = item.results;
                            
                            self.records.each(function(record) {
                                var filter_value = _.filter(results, function(result) {
                                    return _.contains(record.get(item.key), result.id)
                                });
                                record.set(item.key, filter_value);

                                if (filter_value.length > 1) record.set(RELATION_TAG, true);
                            })                        
                        })
                        list.render();
                    })

                    return list;
                });
            });
        },
    })
    
    core.list_widget_registry.add('field.relation_sublist', relation_sublist);
});