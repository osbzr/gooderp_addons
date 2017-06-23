odoo.define('gooderp_pos.main', function(require) {
    "use strict";

    var chrome = require('gooderp_pos.chrome');
    var core = require('web.core');

    core.action_registry.add('pos.ui', chrome.Chrome);

});