
odoo.define('good_portal', function(require) {
    'use strict';
    require('website.website');

    if(!$('.o_website_portal_details').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_website_portal_details'");
    }
});
