/* 
    OpenERP, Open Source Management Solution
    This module copyright (C) 2014 Therp BV (<http://therp.nl>)
                          (C) 2013 Marcel van der Boom <marcel@hsdev.com>
    Copyright (C) 2016 Serpent Consulting Services Pvt. Ltd.
                            (<http://www.serpentcs.com>)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

odoo.define('web.WebTreeImage', function (require) {
    "use strict";
    var core = require('web.core');
    var session = require('web.session');
    var QWeb = core.qweb;
    var list_widget_registry = core.list_widget_registry;

    var WebTreeImage = list_widget_registry.get('field.binary').extend({
        format: function (row_data, options) {
            /* Return a valid img tag. For image fields, test if the
             field's value contains just the binary size and retrieve
            the image from the dedicated controller in that case.
            Otherwise, assume a character field containing either a
            stock Odoo icon name without path or extension or a fully
            fledged location or data url */
            if (!row_data[this.id] || !row_data[this.id].value) {
                return '';
            }
            var value = row_data[this.id].value, src;
            if (this.type === 'binary') {
                if (value && value.substr(0, 10).indexOf(' ') === -1) {
                    // The media subtype (png) seems to be arbitrary
                    src = "data:image/png;base64," + value;
                } else {
                    var imageArgs = {
//                        model: options.model,
                        model:this.model,
                        field: this.id,
                        id: options.id
                    }
                    if (this.resize) {
                        imageArgs.resize = this.resize;
                    }
                    src = session.url('/web/binary/image', imageArgs);
                }
            } else {
                if (!/\//.test(row_data[this.id].value)) {
                    src = '/web/static/src/img/icons/' + row_data[this.id].value + '.png';
                } else {
                    src = row_data[this.id].value;
                }
            }
            return QWeb.render('ListView.row.image', {widget: this, src: src});
        }
    });

    list_widget_registry
    .add('field.image', WebTreeImage)
});
