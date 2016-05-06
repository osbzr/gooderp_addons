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

    function create_vue(model, display_name) {
        var vue = new Vue({
            el: '#container',
            data: {
                model: model,
                display_name: display_name,
                records: [],
                headers: {},
            },
            methods: {
            },
        });

        sync_lists(vue.model).then(function(results) {
            results = JSON.parse(results);
            console.log(results);
            vue.records = results.values;
            vue.headers = results.headers;
        });
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
