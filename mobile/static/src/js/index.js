$(function(){
    // vue对象
    var vue = false,
        origin_data = {
            component_plugin: 'char-input',
            max_count: 0,
            search_word: '',
            display_search_results: true,
            search_cache: false,
            model: '',
            display_name: '',
            records: [],
            headers: {'left': '', 'center': '', 'right': ''},
            footers: {'left': '', 'center': '', 'right': ''},
            form_records: [],
            wizard_records: [],
            search_view: [],
            search_filter: [],
            context: {},
            order_name: '',
            record_form: '',
            order_direction: 'desc',
            loading: false,
            wizard: false,
            editable: false,
        },
        vue_data = {};

    // 参考https://github.com/progrape/router，写一个简单的router
    function getHash(url) {
        return url.indexOf('#/') !== -1 ? url.substring(url.indexOf('#/') + 2) : '/';
    }

    function hashchange(url, stop_animation) {
        var hash = getHash(url),
            home = $('#home'),
            tree = $('#tree'),
            count = $('.gooderp_max_count');

        if (stop_animation) {
            if (hash === '/') {
                home.show();
                tree.hide();
            } else {
                tree.show();
                home.hide();
            }
        } else {
            if (hash === '/') {
                home.addClass('enter').removeClass('leave');
                tree.addClass('leave').removeClass('enter');
            } else {
                tree.addClass('enter').removeClass('leave');
                home.addClass('leave').removeClass('enter');
            }
        }

        if (hash !== '/') {
            init_tree_view(hash);
            count.show();
        } else {
            count.hide();
        }
    }

    window.addEventListener('hashchange', function(event) {
        hashchange(event.newURL);
    });
    hashchange(location.hash, true);

    function refresh_vue_data(options) {
        origin_data.records = [];
        origin_data.search_view = [];
        origin_data.search_filter = [];
        origin_data.form_records = [];
        origin_data.wizard_records = [];
        origin_data.context = {};
        origin_data.headers = {'left': '', 'center': '', 'right': ''};
        origin_data.footers = {'left': '', 'center': '', 'right': ''};

        for (var key in origin_data) {
            vue_data[key] = origin_data[key];
        }
        // vue_data.model = hash;
        for (var options_key in options) {
            vue_data[options_key] = options[options_key];
        }
    }

    function init_tree_view(hash) {
        var reg = new RegExp('-using_wizard$').test(hash);
        refresh_vue_data({
            model: reg? hash.slice(0, hash.length - '-using_wizard'.length) : hash,
            display_name: $('a[href="#/' + hash + '"]').data('display'),
            wizard: reg,
        });

        vue = vue || create_vue(vue_data);
        if (reg) {
            // 用来解决进入tree视图的动画影响到了dialog视图的显示
            $('#tree').css('animation', 'none');
            $.when($.get('/mobile/get_wizard_view', {
                name: vue.model,
            })).then(function(results) {
                vue.wizard_records = JSON.parse(results);
                Vue.nextTick(function () {
                    $('.gooderp_wizard input:first').focus();
                });
            });
        } else {
            vue.do_sync();
        }
    }

    var MAP_OPERATOR = {
        '>': '大于',
        '<': '小与',
        '>=': '大于等于',
        '<=': '小与等于',
        '=': '等于',
        '!=': '不等于',
    };

    function aggregate_sum(key, records) {
        var res = 0;
        records.forEach(function(record) {
            res += record[key];
        });
        return res;
    }

    function aggregate_avg(key, records) {
        var res = 0;
        records.forEach(function(record) {
            res += record[key];
        });
        return records.length? res / records.length: 0;
    }

    function aggregate_min(key, records) {
        var res = records[0][key];
        records.forEach(function(record) {
            if (record[key] < res) {
                res = record[key];
            }
        });
        return res;
    }

    function aggregate_max(key, records) {
        var res = records[0][key];
        records.forEach(function(record) {
            if (record[key] > res) {
                res = record[key];
            }
        });
        return res;
    }

    var AGGREGATE_OPERAOR = {
        'sum': aggregate_sum,
        'avg': aggregate_avg,
        'min': aggregate_min,
        'max': aggregate_max,
    };

    function map_operator(operator) {
        operator = operator || '=';
        return MAP_OPERATOR[operator];
    }

    function sync_lists(name, options) {
        return $.when($.get('/mobile/get_lists', {
            name: name,
            options: JSON.stringify(options || {}),
        }));
    }

    function sync_search_view(name) {
        return $.when($.get('/mobile/get_search_view', {
            name: name,
        }));
    }

    function create_vue(data) {
        var vue = new Vue({
            el: '#container',
            data: data,
            computed: {
                footers: function() {
                    var self = this,
                        footers = {};
                    if (self.records.length > 0) {
                        ['left', 'center', 'right'].forEach(function(key) {
                            if (self.headers[key] && ['float', 'integer'].indexOf(self.headers[key].column) >= 0 && self.headers[key].aggregate) {
                                footers[key] = self._aggerate_func(key);
                            }
                        });
                    }

                    return footers;
                },
            },
            methods: {
                _aggerate_func: function(key) {
                    if (this.headers[key] && this.headers[key].aggregate in AGGREGATE_OPERAOR) {
                        return AGGREGATE_OPERAOR[this.headers[key].aggregate](key, this.records);
                    }
                    return '';
                },
                cancel_wizard: function() {
                    window.history.back();
                },
                confirm_wizard: function() {
                    this.editable = true;
                    if (this.check_wizard_value()) {
                        for (var index in this.wizard_records) {
                            var record = this.wizard_records[index];
                            if (record.type === 'many2one') {
                                this.context[record.name] = [record.id, record.value];
                            } else {
                                this.context[record.name] = record.value;
                            }
                        }

                        this.do_sync(null, null, function() {
                            alert('出现内部错误，请联系管理员修复');
                        });
                    }
                },
                check_wizard_value: function() {
                    for (var index in this.wizard_records) {
                        var record = this.wizard_records[index];
                        if (record.required && !record.value) {
                            return false;
                        }
                    }

                    return true;
                },
                open_form: function(record_id) {
                    var self = this;
                    if (self.record_form === record_id) {
                        self.record_form = '';
                        return;
                    }
                    this.do_sync({
                        type: 'form',
                        record_id: record_id,
                    }, function(results) {
                        self.form_records = JSON.parse(results);
                        self.record_form = record_id;
                    });
                },

                compute_form_header: function(record) {
                    return record.string;
                },
                compute_form_widget: function(record) {
                    if (record.column === 'many2one' && $.isArray(record.value)) {
                        return record.value[1];
                    }

                    return record.value;
                },
                // 参考https://github.com/ElemeFE/vue-infinite-scroll来添加无限滑动
                scroll_container: function() {
                    var container = $('#container'),
                        scrollDistance = container.scrollTop() + container.height();

                    var header = $('.gooderp_tree_header'),
                        tree = $('.gooderp_tree');

                    if (header.css('position') === 'relative' && header.offset().top <= 0) {
                        header.css('position', 'fixed');
                    } else if (header.css('position') === 'fixed' && tree.offset().top >= header.innerHeight()){
                        header.css('position', 'relative');
                    }

                    if (container.prop('scrollHeight') - scrollDistance < 10) {
                        var self = this;
                        return self.do_sync({
                            offset: this.records.length,
                        }, function(results) {
                            results = JSON.parse(results);
                            self.records.splice.apply(self.records, [self.records.length, 0].concat(results.values));
                            self.loading = false;
                        }, null, function() {
                            return this.records.length <= 0 || this.records.length >= this.max_count;
                        });
                    }
                },
                order_by: function(event, headers) {
                    if (this.order_name === headers.name) {
                        this.order_direction = this.order_direction === 'desc'? 'asc' : 'desc';
                    } else {
                        this.order_direction = 'desc';
                    }

                    this.order_name = headers.name;
                    this.do_sync();
                },
                focus_search: function() {
                    this.display_search_results = true;
                },
                blur_search: function() {
                    this.display_search_results = false;
                },
                enter_search: function() {
                    if (this.search_word) {
                        this.add_search(this.search_view[0]);
                    }
                },
                esc_search: function() {
                    if (!this.search_word) {
                        this.search_filter.pop();
                        this.do_sync(null, null, function() { alert('搜索错误'); });
                    }
                },
                cancel_search: function() {
                    this.search_filter = [];
                    this.search_word = '';

                    this.do_sync(null, null, function() { alert('搜索错误'); });
                },
                cancel_filter: function(index) {
                    this.search_filter.splice(index, 1);
                    this.do_sync(null, null, function() { alert('搜索错误'); });
                },
                add_search: function(view) {
                    this.search_filter.push({
                        string: view.string,
                        word: this.search_word,
                        name: view.name,
                        operator: view.operator,
                    });

                    this.search_word = '';
                    this.do_sync(null, null, function() { alert('搜索错误'); });
                },
                do_sync: function(options, success, error, check) {
                    var self = this;
                    self.wizard = false;
                    return this.loadMore(function() {
                        options = options || {};
                        options.domain = options.domain || this.search_filter;
                        options.order = options.order || [this.order_name, this.order_direction].join(' ');
                        options.context = options.context || this.context;
                        return this.sync_records(options, success, error).then(function() {
                            self.loading = false;
                        }, function() {
                            self.loading = false;
                        });
                    }, check);
                },
                loadMore: function(finish, check) {
                    var self = this;
                    if (self.loading) return true;
                    if (check && check.apply(self)) return true;

                    self.loading = true;
                    var progress = 0;
                    var $progress = $('.js_progress');

                    function next() {
                        $progress.css({width: progress + '%'});
                        progress = ++progress % 100;
                        if (self.loading) setTimeout(next, 30);
                        else $progress.css({width: 0});
                    }

                    next();

                    return finish.apply(self);
                },
                map_operator: map_operator,
                choose_operator: function(value) {
                    $('#dialog1').show().on('click', '.weui_cell', function(event) {
                        value.operator = $(this).data('operator');
                        $(this).off('click');
                        $('#dialog1').hide();
                        $('.weui_input').focus();
                    }).one('click', '.weui_btn_dialog, .weui_mask', function(event) {
                        $('#dialog1').hide();
                        $('.weui_input').focus();
                    });
                },
                sync_records: function(options, success, error) {
                    var self = this;
                    success = success || function(results) {
                        results = JSON.parse(results);
                        self.records = results.values;
                        self.headers = results.headers;
                        self.max_count = results.max_count;
                        self.loading = false;
                    };

                    return sync_lists(this.model, options).then(success, error);
                },
                compute_class: function(header) {
                    return header.class || '';
                },
                compute_widget: function(header, field) {
                    if (header.column === 'many2one' && $.isArray(field)) {
                        return field[1];
                    }
                    return field;
                },
            },
        });

        vue.$watch('search_word', function(word) {
            if (!vue.search_cache) {
                sync_search_view(vue.model).then(function(results) {
                    vue.search_view = JSON.parse(results);
                    if (vue.search_view.length <= 0) {
                        vue.search_view = [{
                            name: vue.headers.left.name,
                            string: vue.headers.left.string,
                        }];
                    }
                });
                vue.search_cache = true;
            }
        });

        return vue;
    }
});
