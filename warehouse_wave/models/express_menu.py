# -*- coding: utf-8 -*-

from odoo import models
import hashlib,base64, httplib2
import json, urllib
from odoo.tools.safe_eval import safe_eval

class wh_move(models.Model):
    """
    生成快递电子面单
    """
    _inherit = 'wh.move'

    def get_shipping_type_config(self, type):
        """
        根据传入的快递方式返回相应的参数 
        """
        expressconfigparam = self.env['ir.config_parameter']
        ytousername = expressconfigparam.get_param('express_menu_yto_user_name', default='')
        ytomonthcode = expressconfigparam.get_param('express_menu_yto_month_code', default='')
        shipping_type_config = {'YTO': {'ShipperCode': 'YTO',
                                        'CustomerName': ytousername,
                                        'MonthCode': ytomonthcode},
                                'SF': {'ShipperCode': 'SF'}}
        return shipping_type_config.get(type)


    def get_sender(self, warehouse_id):
        ware_hosue_row = self.env['warehouse'].browse(warehouse_id)
        sender = {
            'Company': 'LV', 'Name': 'Taylor', 'Mobile': '15018442396', 'ProvinceName': '上海',
            'CityName': '上海', 'ExpAreaName': '青浦区', 'Address': '明珠路73号'}
        return sender

    def get_receiver_goods_message(self, order_code):
        receiver = {'Company': 'GCCUI', 'Name': 'Yann', 'Mobile': '15018442396',
                    'ProvinceName': '北京', 'CityName': '北京', 'ExpAreaName': '朝阳区',
                    'Address': '三里屯街道雅秀大厦'}
        goods = [{'GoodsName': '鞋子', 'Goodsquantity': 1, 'GoodsWeight': 1.0}]
        remark = '小心轻放'
        shipping_type = 'SF' or 'YTO'
        return receiver, goods, remark, shipping_type

    def get_express_menu(self):
        expressconfigparam = self.env['ir.config_parameter']
        appid = expressconfigparam.get_param('express_menu_app_id', default='')
        appkey = expressconfigparam.get_param('express_menu_app_key', default='')
        path = expressconfigparam.get_param('express_menu_oder_url', default='')
        header = safe_eval(expressconfigparam.get_param('express_menu_request_headers',
                                                        default=''))
        order_code = '012657700389'
        sender = self.get_sender(1)
        receiver, commodity, remark, shipping_type = self.get_receiver_goods_message(order_code)
        request_data = dict(OrderCode=order_code, PayType=1, ExpType=1, Cost=1.0, OtherCost=1.0,
                            Sender=sender, Receiver=receiver, Commodity=commodity, Weight=1.0,
                            Quantity=1, Volume=0.0, Remark=remark, IsReturnPrintTemplate=1)
        request_data.update(self.get_shipping_type_config(shipping_type))
        request_data = json.dumps(request_data)
        data = {'RequestData': request_data,
                'EBusinessID': appid,
                'RequestType': '1007',
                'DataType': '2',
                'DataSign': self.encrypt_kdn(request_data, appkey)}
        http = httplib2.Http()
        response, content = http.request(path, 'POST', headers=header, body=urllib.urlencode(data))
        print response
        content = content.replace('true', 'True').replace('false', 'False')
        return safe_eval(content).get('PrintTemplate')


    def encrypt_kdn(self, data, appkey):
        
        key = base64.b64encode(hashlib.md5("%s%s" % (data, appkey)).hexdigest(), altchars=None)
        return urllib.quote(key, safe='/')

