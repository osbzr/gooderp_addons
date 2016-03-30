openerp.web_sublist = function(instance) {
    var QWeb = instance.web.qweb;
    var RELATION_TAG = 'RELATION_SUBLIST_MULTI';

    instance.web_sublist.relationSublist = instance.web.list.Column.extend({
        _format: function(row_data, options) {
            if (this.widget === 'relation_sublist') {

                var values = row_data[this.id]['value'],
                    options = instance.web.py_eval(this.options || '{}'),
                    field_value = _.map(_.map(values, function(value) { return value[options.field]; }), function(value) {
                        return _.isArray(value)? value[1]: value;
                    });

                // 通过without去除掉undefined的值
                return QWeb.render('web_sublist.sublist', {'values': _.without(field_value, undefined)}).trim();
            } else {
                return this._super(row_data, options);
            };

        },
    });

    instance.web.ListView.Groups.include({
        render_dataset: function(dataset) {
            var self = this,
                deferred = this._super.apply(this, arguments);

            return deferred.then(function(list) {
                var containers = {}

                // 统计需要定义子列表的字段
                _.each(list.columns, function(column) {
                    if (column.widget === 'relation_sublist') {
                        var options = instance.web.py_eval(column.options || '{}');
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

                // 根据子列表的model、field、ids来取值
                _.each(_.keys(containers), function(key) {
                    var container = containers[key];
                    new instance.web.Model(container.relation).call('read', [container.ids, container.fields]).then(function(results) {
                        self.records.each(function(record) {
                            var filter_value = _.filter(results, function(result) {
                                return _.contains(record.get(key), result.id)
                            });
                            record.set(key, filter_value);

                            if (filter_value.length > 1) record.set(RELATION_TAG, true);
                        });
                    })
                });

                return list
            });
        }
    })

    instance.web.list.columns.add('field.relation_sublist', 'instance.web_sublist.relationSublist');

};