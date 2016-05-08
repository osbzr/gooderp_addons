$(function(){
    var router = new Router({
        container: '#container',
        enterTimeout: 250,
        leaveTimeout: 250,
    });

    var routes = {'/': {
        url: '/',
        className: 'home',
        render: function () {
            return $('#home').html();
        }
    }};

    var MAP_OPERATOR = {
        '>': '大于',
        '<': '小与',
        '>=': '大于等于',
        '<=': '小与等于',
        '=': '等于',
        '!=': '不等于',
    };

    function map_operator(operator) {
        operator = operator || '=';
        return MAP_OPERATOR[operator];
    }

    function sync_lists(name, options) {
        return $.when($.get('/mobile/get_lists', {
            name: name,
            options: JSON.stringify(options || {}),
            // options: {
            //     domain: domain,
            //     offset: offset,
            //     limit: limit,
            //     order: order,
            //     type: type || 'tree', // 获取数据来源是tree还是form
            //     record_id: record_id,
            // }
        }));
    }

    function sync_search_view(name) {
        return $.when($.get('/mobile/get_search_view', {
            name: name,
        }));
    }

    function create_vue(model, display_name) {
        var vue = new Vue({
            el: '#container',
            data: {
                search_word: '',
                search_cache: false,
                model: model,
                display_name: display_name,
                records: [],
                headers: {},
                search_view: [],
                search_filter: [],
            },
            methods: {
                enter_search: function() {
                    if (this.search_word) {
                        this.add_search(this.search_view[0]);
                    }
                },
                esc_search: function() {
                    if (!this.search_word) {
                        this.search_filter.pop();
                        this.do_search();
                    }
                },
                cancel_search: function() {
                    this.search_filter = [];
                    this.search_word = '';

                    this.do_search();
                },
                cancel_filter: function(index) {
                    this.search_filter.splice(index, 1);
                },
                add_search: function(view) {
                    this.search_filter.push({
                        string: view.string,
                        word: this.search_word,
                        name: view.name,
                        operator: view.operator,
                    });

                    this.search_word = '';
                    this.do_search();
                },
                do_search: function() {
                    this.sync_records({
                        domain: this.search_filter
                    });
                },
                map_operator: map_operator,
                choose_operator: function(value) {
                    $('#dialog1').show().on('click', '.weui_cell', function(event) {
                        value.operator = $(this).data('operator');
                        $(this).off('click');
                        $('#dialog1').hide();
                    }).one('click', '.weui_btn_dialog, .weui_mask', function(event) {
                        $('#dialog1').hide();
                    });
                },
                sync_records: function(options) {
                    sync_lists(this.model, options).then(function(results) {
                        results = JSON.parse(results);
                        vue.records = results.values;
                        vue.headers = results.headers;
                    }, function() {
                        alert('搜索错误');
                    });
                },
            },
        });

        vue.$watch('search_word', function(word) {
            if (!vue.search_cache) {
                sync_search_view(vue.model).then(function(results) {
                    console.log(results);
                    vue.search_view = JSON.parse(results);
                });
                vue.search_cache = true;
            }
        });

        vue.sync_records();
    }

    $('.weui_grid').each(function(index, grid) {
        var grid_name = $(grid).attr('href').slice(2);
        routes[grid_name] = {
            url: '/' + grid_name,
            className: grid_name,
            render: function() {
                return $('#tree').html();
            },
            bind: function() {
                create_vue(grid_name, $(grid).data('display'));
            },
        };
    });

    for (var route in routes) {
        router.push(routes[route]);
    }

    router.setDefault('/').init();
});
