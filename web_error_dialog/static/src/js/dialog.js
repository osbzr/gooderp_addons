odoo.define('web.gooderp_dialog', function(require) {
    var crash_manager = require('web.CrashManager');
    var core = require('web.core');
    var session = require('web.session');
    var Dialog = require('web.Dialog');
    
    // 自定义填充按钮，一个对象列表，规则如下
    // @text: 按钮的显示文本
    // @classes: 按钮的class
    // @click：参数为点击事件event的函数
    // @close：一个Bool字段，当click属性没值且该值为true的时候点击默认关闭
    var open_help_page = function () {
        window.open("http://shang.qq.com/wpa/qunwpa?idkey=f0b47f9891e6f5361c4bdc841c424eb13035d981da9451995eca13cb42273725");
    };
    var warning_buttons = error_buttons = message_buttons = default_buttons =
        [{text: core._t("确定"), close: true, classes: 'btn btn-primary'},
            {text: core._t("请求官方服务"), click: open_help_page, classes: 'btn btn-warning'}];

    crash_manager.include({
        show_warning: function(error) {
            if (!this.active) {
                return;
            }
            var audio;
            audio = new Audio();
            audio.src = session.url("/gooderp_pos/static/src/sounds/error.wav");
            audio.play();
            new Dialog(this, {
                size: 'medium',
                title: "Gooderp " + (_.str.capitalize(error.type) || core._t("Warning")),
                subtitle: error.data.title,
                $content: $('<div>').html(core.qweb.render('CrashManager.warning', {error: error})),
                buttons: warning_buttons || default_buttons || warning_buttons,
            }).open();
        },
        show_error: function(error) {
            if (!this.active) {
                return;
            }
            new Dialog(this, {
                title: "Gooderp " + _.str.capitalize(error.type),
                $content: core.qweb.render('CrashManager.error', {error: error}),
                buttons: error.buttons || error_buttons || default_buttons || warning_buttons,
            }).open();
        },
        show_message: function(exception) {
            this.show_error({
                type: core._t("Client Error"),
                message: exception,
                data: {debug: ""},
                buttons: message_buttons || warning_buttons,
            });
        },
    })
})