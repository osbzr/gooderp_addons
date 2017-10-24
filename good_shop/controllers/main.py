# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from werkzeug.exceptions import Forbidden

from odoo import http, tools
from odoo.http import request
from odoo.addons.base.ir.ir_qweb.fields import nl2br
from odoo.addons.website.models.website import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.exceptions import ValidationError
# from odoo.addons.website_form.controllers.main import WebsiteForm

_logger = logging.getLogger(__name__)

PPG = 20  # Products Per Page
PPR = 4   # Products Per Row


class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= PPR:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=PPG):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % PPR, pos / PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) / PPR) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos / PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos / PPR) + y2][(pos % PPR) + x2] = False
            self.table[pos / PPR][pos % PPR] = {
                'product': p, 'x': x, 'y': y,
                'class': " ".join(map(lambda x: x.html_class or '', p.website_style_ids))
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos / PPR))
            index += 1

        # Format table according to HTML needs
        rows = self.table.items()
        rows.sort()
        rows = map(lambda x: x[1], rows)
        for col in range(len(rows)):
            cols = rows[col].items()
            cols.sort()
            x += len(cols)
            rows[col] = [c for c in map(lambda x: x[1], cols) if c]

        return rows

        # TODO keep with input type hidden


# class WebsiteSaleForm(WebsiteForm):
#
#     @http.route('/website_form/shop.sale.order', type='http', auth="public", methods=['POST'], website=True)
#     def website_form_saleorder(self, **kwargs):
#         model_record = request.env.ref('sale.model_sale_order')
#         try:
#             data = self.extract_data(model_record, kwargs)
#         except ValidationError, e:
#             return json.dumps({'error_fields': e.args[0]})
#
#         order = request.website.sale_get_order()
#         if data['record']:
#             order.write(data['record'])
#
#         if data['custom']:
#             values = {
#                 'body': nl2br(data['custom']),
#                 'model': 'sale.order',
#                 'message_type': 'comment',
#                 'no_auto_thread': False,
#                 'res_id': order.id,
#             }
#             request.env['mail.message'].sudo().create(values)
#
#         if data['attachments']:
#             self.insert_attachment(model_record, order.id, data['attachments'])
#
#         return json.dumps({'id': order.id})


class WebsiteSale(http.Controller):

    def get_attribute_value_ids(self, product):
        """ 产品的属性列表

        :return: 产品属性列表
           [attribute id, [attribute ids], price, sale price]
        """
        # product attributes with at least two choices
        quantity = product._context.get('quantity') or 1
        product = product.with_context(quantity=quantity)

        attribute_ids = []
        for attribute in product.attribute_ids:
            attribute_ids.append(
                [attribute.id, product.attribute_ids, product.price, product.price])

        return attribute_ids

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        return 'website_published desc,%s , id desc' % post.get('order', 'website_sequence desc')

    def _get_search_domain(self, search, category, attrib_values):
        #         domain = request.website.sale_product_domain()
        domain = []
        if search:
            for srch in search.split(" "):
                domain += [('name', 'ilike', srch)]

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_ids.value_ids', 'in', ids)]

        return domain

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attributes_ids = set([v[0] for v in attrib_values])
        attrib_set = set([v[1] for v in attrib_values])

        domain = self._get_search_domain(search, category, attrib_values)
        domain += [('not_saleable', '=', False)]

        keep = QueryURL('/shop', category=category and int(category),
                        search=search, attrib=attrib_list, order=post.get('order'))

        request.context = dict(
            request.context, partner=request.env.user.gooderp_partner_id)

        url = "/shop"
        if search:
            post["search"] = search
        if category:
            category = request.env['goods.class'].browse(int(category))
            url = "/shop/category/%s" % slug(category)
        if attrib_list:
            post['attrib'] = attrib_list

#         categs = request.env['product.public.category'].search([('parent_id', '=', False)])
        Product = request.env['goods']

        parent_category_ids = []
        if category:
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id

        product_count = Product.search_count(domain)
        pager = request.website.pager(
            url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = Product.search(domain, limit=ppg, offset=pager['offset'])

        ProductAttribute = request.env['attribute']
        if products:
            # get all products without limit
            selected_products = Product.search(domain, limit=False)
            attributes = ProductAttribute.search(
                [('goods_id', 'in', selected_products.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        # 币别
        for user in request.env['res.users'].browse(request.uid):
            currency = user.company_id.currency_id

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'products': products,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg),
            'rows': PPR,
            'attributes': attributes,
            'keep': keep,
            'parent_category_ids': parent_category_ids,
            'currency': currency,
        }
        if category:
            values['main_object'] = category
        return request.render("good_shop.products", values)

    # 点击界面上的某一个产品
    @http.route(['/shop/product/<model("goods"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        product_context = dict(request.env.context,
                               active_id=product.id,
                               partner=request.env.user.gooderp_partner_id)
        ProductCategory = request.env['goods.class']
#         Rating = request.env['rating.rating']

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id,
                        search=search, attrib=attrib_list)

        if not product_context.get('pricelist'):
            #             product_context['pricelist'] = pricelist.id
            product = product.with_context(product_context)

        attribute_dict = {}
        for attribute in product.attribute_ids:
            for value in attribute.value_ids:
                if not attribute_dict.has_key(value.category_id.name):
                    attribute_dict.update(
                        {value.category_id.name: [value.value_id.name]})
                else:
                    if value.value_id.name in attribute_dict[value.category_id.name]:
                        continue
                    else:
                        attribute_dict[value.category_id.name].append(
                            value.value_id.name)

        # 货币取当前登录用户公司对应的货币
        for user in request.env['res.users'].browse(request.uid):
            currency = user.company_id.currency_id

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'keep': keep,
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'currency': currency,
            'attribute_dict': attribute_dict,
        }
        return request.render("good_shop.product", values)

    # 点击购物车
    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()

        values = {
            'website_sale_order': order,
            'compute_currency': lambda price: price,
            'suggested_products': [],
        }

        if post.get('type') == 'popover':
            return request.render("good_shop.cart_popover", values)

        if post.get('code_not_available'):
            values['code_not_available'] = post.get('code_not_available')

        return request.render("good_shop.cart", values)

    # 点击 加入购物车
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        request.website.sale_get_order(force_create=1)._cart_update(
            product_id=int(product_id),
            add_qty=float(add_qty),
            set_qty=float(set_qty),
            attributes=self._filter_attributes(**kw),
        )

        # 进入购物车
        return request.redirect("/shop/cart")

    def _filter_attributes(self, **kw):
        return {k: v for k, v in kw.items() if "attribute" in k}

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True):
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            return {}

        value = order._cart_update(
            product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty)
        if not order.cart_quantity:
            request.website.sale_reset()
            return {}
        if not display:
            return None

        order = request.website.sale_get_order()
        value['cart_quantity'] = order.cart_quantity
#         from_currency = order.company_id.currency_id
#         to_currency = order.pricelist_id.currency_id
        value['good_shop.cart_lines'] = request.env['ir.ui.view'].render_template("good_shop.cart_lines", {
            'website_sale_order': order,
            'compute_currency': lambda price: price,
            #             'suggested_products': order._cart_accessories()
        })
        return value

    def _get_mandatory_billing_fields(self):
        return ["name", "address"]  # , "city", "country_id"

    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        if order.partner_id.id == request.website.user_id.sudo().gooderp_partner_id.id:
            return request.redirect('/shop/address')

        for f in self._get_mandatory_billing_fields():
            if not order.partner_id[f]:
                return request.redirect('/shop/address?partner_id=%d' % order.partner_id.id)

        values = self.checkout_values(**post)

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("good_shop.checkout", values)

    # ------------------------------------------------------
    # Checkout
    # ------------------------------------------------------

    def checkout_redirection(self, order):
        ''' 重定向 '''
        # must have a draft sale order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # ？？？？？？？？？？？
        # if transaction pending / done: redirect to confirmation
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self, **kw):
        order = request.website.sale_get_order(force_create=1)
        shippings = []
        if order.partner_id != request.website.user_id.sudo().gooderp_partner_id:
            Partner = order.partner_id.with_context(show_address=1).sudo()
            shippings = Partner.search([
                ("id", "=", order.partner_id.id),
            ], order='id desc')

        values = {
            'order': order,
            'shippings': shippings,
            'only_services': order and order.only_services or False
        }
        return values

    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True)
    def address(self, **kw):
        Partner = request.env['partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        mode = (False, False)
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().gooderp_partner_id.id:
            mode = ('new', 'billing')

        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                else:
                    shippings = Partner.search(
                        [('id', '=', order.partner_id.id)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(
                mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(
                order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._checkout_form_save(mode, post, kw)

                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.onchange_partner_id()
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                if not errors:
                    return request.redirect(kw.get('callback') or '/shop/checkout')

        country = request.env.ref('partner_address.cn')
        render_values = {
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'country': country,
            "states": request.env['country.state'].sudo().search([('country_id', '=', country.id)]),
            'error': errors,
            'callback': kw.get('callback'),
        }
        return request.render("good_shop.address", render_values)

    def values_preprocess(self, order, mode, values):
        return values

    def values_postprocess(self, order, mode, values, errors, error_msg):
        new_values = {}
        for k, v in values.items():
            # don't drop empty value, it could be a field to reset
            new_values[k] = v

        new_values['customer'] = True

#         if mode == ('edit', 'billing') and order.partner_id.type == 'contact':
#             new_values['type'] = 'other'
#         if mode[1] == 'shipping':
#             new_values['parent_id'] = order.partner_id.commercial_partner_id.id
#             new_values['type'] = 'delivery'

        return new_values, errors, error_msg

    def checkout_form_validate(self, mode, all_form_values, data):
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []

        # Required fields from form
        required_fields = filter(
            None, (all_form_values.get('field_required') or '').split(','))
        # Required fields from mandatory field function
        required_fields += mode[1] == 'shipping' and self._get_mandatory_shipping_fields(
        ) or self._get_mandatory_billing_fields()

        # error message for empty required fields
        for field_name in required_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(u'请输入有效的邮箱地址！')

        if [err for err in error.values() if err == 'missing']:
            error_message.append(u'必输字段不能为空')

        return error, error_message

    def _checkout_form_save(self, mode, checkout, all_values):
        Partner = request.env['partner']
        if mode[0] == 'new':
            partner_id = Partner.sudo().create(checkout)
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                # double check
                order = request.website.sale_get_order()
                if partner_id != order.partner_id.id:
                    return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
                order.address = checkout['address']
                order.mobile = checkout['mobile']
        return partner_id

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        order = request.website.sale_get_order()
        request.website.sell_order_to_delivery()

        # 订单创建成功，清空购物车
        redirection = self.checkout_redirection(order)
        if redirection:
            return request.render("good_shop.success")
