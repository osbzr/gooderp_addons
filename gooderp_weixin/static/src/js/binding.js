// If we need to use custom DOM library, let's save it to $ variable:

// localStorage.host = '192.168.1.117';
// localStorage.port = 11111;

// Initialize app
// var App = new Framework7({
//     modalTitle: '',
//     //模板自动编译
//     precompileTemplates: true,
//     //浏览器可以前进后退
//     pushState: true,
//     //滑动返回上一页
//     swipeBackPage:true,
//     swipeBackPageAnimateShadow:false,
//     swipeBackPageAnimateOpacity:false,
//     swipeBackPageActiveArea:30,
//     swipeBackPageThreshold:0,
//     //使用JS滚动条（参见 iscroll),这样就不会不满屏幕就出现滚动条
//     scroller:"js"
// });

avalon.define({
    $id: "cancel-binding",
    result: '',
    //取消绑定请求
    do_cancel_binding: function() {
        $.showIndicator();
        var url = '/weixin/do_cancel_binding'

        $.getJSON(url, function(json) {
            vm.result = json.result
            $.hideIndicator();
        });
    }
});

var vm = avalon.define({
    $id: "binding-form",
    can_binding: true,
    uid: '',
    partner_id: '',
    login_id: '',
    no_partner: false,
    mobile: '',

    do_binding: function() {
        if (vm.can_binding) {
            $.showIndicator();
            $.getJSON('/weixin/do_binding', {
                user_id: $('#hidden_user').val(),
                // auth_code: vm.auth_code
            }, function(json) {
                //vm.auth_code = json.partner_id + ', ' + json.uid
                if (json.no_partner) {
                    vm.no_partner = true;
                    $.hideIndicator();
                    return;
                }

                vm.partner_id = json.partner_id;
                vm.uid = json.uid;
                vm.login_id = json.login_id;
                vm.mobile = json.mobile;

                var user_id = json.user_id;
                var access_token = json.access_token;

                $.hideIndicator();
                if (!json.partner_id) {
                    $.alert('您输入的手机号码无法绑定!');
                } else {
                    $.getJSON('https://qyapi.weixin.qq.com/cgi-bin/user/authsucc', {
                        access_token: access_token,
                        userid: user_id,
                    });
                }
            });
        }
    }
});

var success = function(data, textStatus, jqXHR) {
    // We have received response and can hide activity indicator
    $.hideIndicator();
    // Will pass context with retrieved user name
    // to welcome page. Redirect to welcome page
    data = JSON.parse(data);
    if (data.partner_id) {
        $.alert('绑定成功');
    }
};

var notsuccess = function(data, textStatus, jqXHR) {
    // We have received response and can hide activity indicator
    $.hideIndicator();
    $.alert('Login was unsuccessful, please try again');
};
