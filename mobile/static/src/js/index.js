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

    function sync_lists(name, domain, offset, limit) {
        return $.when($.get('/mobile/get_lists', {
            name: name,
            domain: domain,
            offset: offset,
            limit: limit,
        }));
    }

    function create_vue(model) {
        sync_lists('goods', 'i', 0, 80).then(function(results) {
            console.log(results);
        });

        new Vue({
            el: '#container',
            data: {
                message: model,
                records: [{'field': 'nihao'}, {'field': 'sm'}, {'field': 'hha'}],
            },
            methods: {
            },
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
                create_vue(grid_name);
            },
        };
    });

    for (var route in routes) {
        router.push(routes[route]);
    }

    router.setDefault('/').init();
});
