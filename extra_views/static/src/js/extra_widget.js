odoo.define('ExtraWidget', function(require) {
    "use strict";

    var config = require('web.config');
    var core = require('web.core');
    var Model = require('web.DataModel');
    var formats = require('web.formats');
    var Widget = require('web.Widget');

    var _t = core._t;
    var QWeb = core.qweb;

    // hide top legend when too many item for device size
    var MAX_LEGEND_LENGTH = 25 * (1 + config.device.size_class);

    return Widget.extend({
        className: "o_extra_svg_container",
        init: function(parent, model, options) {
            this._super(parent);
            this.context = options.context;
            this.fields = options.fields;
            this.fields.__count__ = { string: _t("Count"), type: "integer" };
            this.model = new Model(model, { group_by_no_leaf: true });

            this.domain = options.domain || [];
            this.groupbys = options.groupbys || [];
            this.mode = options.mode || "bar";
            this.measure = options.measure || "__count__";
            this.stacked = options.stacked;
            this.name = this.getParent().ViewManager.title;
        },
        start: function() {
            return this.load_data().then(this.proxy('display_graph'));
        },
        update_data: function(domain, groupbys) {
            this.domain = domain;
            this.groupbys = groupbys;
            return this.load_data().then(this.proxy('display_graph'));
        },
        set_mode: function(mode) {
            this.mode = mode;
            this.display_graph();
        },
        set_measure: function(measure) {
            this.measure = measure;
            return this.load_data().then(this.proxy('display_graph'));
        },
        load_data: function() {
            var fields = this.groupbys.slice(0);
            if (this.measure !== '__count__'.slice(0))
                fields = fields.concat(this.measure);
            return this.model
                .query(fields)
                .filter(this.domain)
                .context(this.context)
                .lazy(false)
                .group_by(this.groupbys.slice(0, 2))
                .then(this.proxy('prepare_data'));
        },
        prepare_data: function() {
            var raw_data = arguments[0],
                is_count = this.measure === '__count__';
            var data_pt, j, values, value;

            this.data = [];
            this.labels = []
            for (var i = 0; i < raw_data.length; i++) {
                data_pt = raw_data[i].attributes;
                values = [];
                if (this.groupbys.length === 1) data_pt.value = [data_pt.value];
                for (j = 0; j < data_pt.value.length; j++) {
                    values[j] = this.sanitize_value(data_pt.value[j], data_pt.grouped_on[j]);
                    if (this.labels.length > j) {
                        this.labels[j].push(values[j])
                    } else {
                        this.labels.push([])
                        this.labels[j].push(values[j])
                    }
                }
                value = is_count ? data_pt.length : data_pt.aggregates[this.measure];

                this.data.push({
                    labels: values,
                    value: value
                });
            }
        },
        sanitize_value: function(value, field) {
            if (value === false) return _t("Undefined");
            if (value instanceof Array) return value[1];
            if (field && this.fields[field] && (this.fields[field].type === 'selection')) {
                var selected = _.where(this.fields[field].selection, { 0: value })[0];
                return selected ? selected[1] : value;
            }
            return value;
        },
        display_graph: function() {
            if (this.to_remove) {
                nv.utils.offWindowResize(this.to_remove);
            }
            this.$el.empty();
            if (!this.data.length) {
                this.$el.append(QWeb.render('ExtraViews.error', {
                    title: _t("No data to display"),
                    description: _t("No data available for this chart. " +
                        "Try to add some records, or make sure that " +
                        "there is no active filter in the search bar."),
                }));
            } else {
                this.display_views();
            }
        },
        display_views: function() {
            var self = this;
            var myChart = echarts.init(self.$el.parents().find('#main')[0]);
            var option = self.get_options()
            myChart.setOption(option, true);
            return myChart;
        },
        get_options: function() {
            var self = this;
            return eval("self.get_" + self.mode + "_option()");
        },
        prepare_bar_data: function() {
            var self = this;
            _.each(self.data, function(data_row) {
                if (self.xaxis_data && !self.legend_data) {
                    self.series_data.push(data_row.value);
                } else if (self.xaxis_data && self.legend_data) {
                    var row_index = self.series_data.find(function(row) {
                        return row.name === data_row.labels[1];
                    });
                    if (row_index) {
                        row_index.data.push(data_row.value)
                    } else {
                        self.series_data.push({
                            'name': data_row.labels[1],
                            'type': 'bar',
                            'stack': self.context.bar_type && data_row.labels[1] || 'sum',
                            'data': [data_row.value]
                        });
                    };
                };
            });

        },
        get_bar_option: function() {
            var self = this;
            self.legend_data = this.labels && _.unique(this.labels[1]) || [];
            self.xaxis_data = this.labels && _.unique(this.labels[0]) || [];
            self.series_data = [];
            self.prepare_bar_data();
            var option = {

                tooltip: {
                    show: true
                },
                toolbox: self.bar_tool_box(),
                calculable: true,
                legend: {
                    data: self.legend_data || []
                },
                xAxis: [{
                    type: 'category',
                    data: self.xaxis_data || []
                }],
                yAxis: [{
                    type: 'value'
                }],
                series: self.series_data || [],
            }
            return option;
        },
        prepare_pie_data: function() {
            var self = this;
            _.each(self.data, function(data_row) {
                var row_index = self.series_data.find(function(row) {
                    return row.name === data_row.labels[0];
                })
                if (row_index) {
                    row_index.value += data_row.value
                } else {
                    self.series_data.push({ 'value': data_row.value, 'name': data_row.labels[0] })
                }
            });
        },
        get_pie_option: function() {
            var self = this;
            self.legend_data = this.labels && _.unique(this.labels[1]) || [];
            self.xaxis_data = this.labels && _.unique(this.labels[0]) || [];
            self.series_data = [];
            self.prepare_pie_data();
            var option = {
                title: {
                    text: self.name,
                    x: 'center'
                },
                tooltip: {
                    trigger: 'item',
                    formatter: "{a} <br/>{b} : {c} ({d}%)"
                },
                legend: {
                    orient: 'vertical',
                    x: 'left',
                    data: self.xaxis_data
                },
                toolbox: self.pie_tool_box(),
                calculable: true,
                series: [{
                    name: self.name,
                    type: 'pie',
                    radius: '55%',
                    center: ['50%', '60%'],
                    data: self.series_data,
                }],
            };
            return option;
        },

        bar_tool_box: function() {
            var toolbox = {
                show: true,
                feature: {
                    mark: { show: true },
                    dataView: { show: true, readOnly: false },
                    magicType: { show: true, type: ['line', 'bar', 'stack', 'tiled'] },
                    restore: { show: true },
                    saveAsImage: { show: true }
                }
            };
            return toolbox;
        },

        pie_tool_box: function() {
            var toolbox = {
                show: true,
                feature: {
                    mark: { show: true },
                    dataView: { show: true, readOnly: false },
                    magicType: {
                        show: true,
                        type: ['pie', 'funnel'],
                        option: {
                            funnel: {
                                x: '25%',
                                width: '50%',
                                funnelAlign: 'left',
                                max: Math.max(self.series_data)
                            }
                        }
                    },
                    restore: { show: true },
                    saveAsImage: { show: true }
                }
            };
            return toolbox;
        }
    });
});