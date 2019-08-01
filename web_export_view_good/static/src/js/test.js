odoo.define('web_export_view_good.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('web_export_view_good_tour', [{
    url: '/web',
    test: true},{
    trigger: '.o_main .o_main_content .o_control_panel .o_cp_left .o_list_buttons .o_button_export',
    content:"OKKK",
    run: 'click',
}, {    content: "click on style dropdown",
    }]);

});



