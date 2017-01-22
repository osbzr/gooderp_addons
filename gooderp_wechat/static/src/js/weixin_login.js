$(function() {
    var PULLING_TIME = 2000;
    function pulling() {
        $.when($.get('/wechat/pulling')).then(function(res) {
            if (res == 'error') {
                setTimeout(pulling, PULLING_TIME);
            } else if (res == 'ok') {
                window.location = '/';
            }
        });
    }
    if (window.location.pathname.endsWith('/web/login')) {
        setTimeout(pulling, PULLING_TIME);
    }
});
