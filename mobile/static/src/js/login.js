$(function() {
    var db = $('.gooderp_db select'),
        account = $('.gooderp_login_account input'),
        passwd = $('.gooderp_login_password input'),
        account_message = $('.gooderp_login_account .gooderp_login_message'),
        passwd_message = $('.gooderp_login_password .gooderp_login_message'),
        button = $('#gooderp_login_button');

    account.focus();

    function check_value() {
        account_message.fadeOut();
        passwd_message.fadeOut();

        if (!account.val()) {
            account_message.fadeIn('fast').text('帐号必输');
        }

        if (!passwd.val()) {
            passwd_message.fadeIn('fast').text('密码必输');
        }

        return account.val() && passwd.val();
    }

    function login() {
        if (check_value()) {
            $.when($.post('/mobile/db_login', {
                db: db.val(),
                account: account.val(),
                passwd: passwd.val(),
            })).then(function(res) {
                if (res === 'ok') {
                    location.href = '/mobile/home';
                } else {
                    passwd_message.fadeIn('fast').text(res);
                }
            });
        }
    }

    button.on('click', login);

    account.on('keydown', function(event) {
        if (event.keyCode === 13) {
            passwd.focus();
        }
    });

    passwd.on('keydown', function(event) {
        if (event.keyCode === 13) {
            login();
        }
    });
});
