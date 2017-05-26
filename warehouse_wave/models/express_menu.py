# -*- coding: utf-8 -*-

from odoo import models, fields, api
import hashlib,base64, httplib2
import json, urllib
from odoo.tools.safe_eval import safe_eval
import pdfkit
import tempfile, os

class express_menu_config(models.Model):
    """
    快递面单设置 目前只支持 下面这几个快递
    EMS 顺丰 圆通 百世 中通 韵达 申通 德邦 宅急送 京东 信丰 全峰 跨越速运 安能 快捷 天天 国通 优速
    """
    _name = 'express.menu.config'
    name = fields.Char(u'快递公司名称', required=True)
    abbreviation = fields.Char(u'简称', required=True)
    customername = fields.Char(u'客户名称')
    customerpwd = fields.Char(u'客户密码')
    monthcode = fields.Char(u'月结号')
    sendsite = fields.Char(u'发送站点')
    logisticcode = fields.Char(u'快递单号')

class warehouse(models.Model):
    _name = 'warehouse'
    _inherit = ['warehouse', 'state.city.county']
    detail_address = fields.Char(u'详细地址')
    principal_id = fields.Many2one('staff', u'负责人')


class sell_delivery(models.Model):

    _inherit = 'sell.delivery'

    @api.multi
    def get_express_menu(self):
        """销售发货单 获取 快递面单"""
        return self.sell_move_id.get_express_menu()


class wh_move(models.Model):
    """
    生成快递电子面单
    """
    _inherit = 'wh.move'
    express_menu = fields.Html(u'快递面单')

    def get_shipping_type_config(self, menu_type):
        """
        根据传入的快递方式返回相应的参数
        """
        express_menu = self.env['express.menu.config'].search([('abbreviation', '=', menu_type)])
        shipping_type_config = dict(ShipperCode=menu_type,
                                    CustomerName=express_menu.customername or '',
                                    CustomerPwd=express_menu.customerpwd or '',
                                    MonthCode=express_menu.monthcode or '',
                                    SendSite=express_menu.sendsite or '',
                                    )
        return shipping_type_config

    def get_sender(self, ware_hosue_row):
        sender = dict(Company=ware_hosue_row.company_id.name,
                      Name=ware_hosue_row.principal_id.name or ware_hosue_row.company_id.name or '',
                      Mobile=ware_hosue_row.principal_id.work_phone or
                      ware_hosue_row.company_id.phone,
                      ProvinceName=ware_hosue_row.province_id.name  or '',
                      CityName=ware_hosue_row.city_id.city_name or '',
                      ExpAreaName=ware_hosue_row.county_id.county_name  or '',
                      Address=ware_hosue_row.detail_address or '')
        return sender

    def get_receiver_goods_message(self):
        receiver = dict(Company='GGG',
                        Name=self.partner_id.name,
                        Mobile=self.partner_id.main_mobile,
                        ProvinceName='北京',
                        CityName='北京',
                        ExpAreaName='朝阳区',
                        Address='三里屯街道雅秀大厦')
        goods = []
        for line in self.line_out_ids:
            goods.append(dict(GoodsName=line.goods_id.name, #产品名称
                              Goodsquantity=int(line.goods_qty), #产品数量
                              GoodsWeight=1.0, #产品重量
                              GoodsCode=line.goods_id.code or '', # 产品编码
                              GoodsPrice=0.0, #产品价格
                              # GoodsVol='',  #产品体积
                              ))
        return receiver, goods

    @api.model
    def get_express_menu(self):
        expressconfigparam = self.env['ir.config_parameter']
        appid = expressconfigparam.get_param('express_menu_app_id', default='')
        appkey = expressconfigparam.get_param('express_menu_app_key', default='')
        path = expressconfigparam.get_param('express_menu_oder_url', default='')
        header = safe_eval(expressconfigparam.get_param('express_menu_request_headers',
                                                        default=''))
        order_code = self.name
        sender = self.get_sender(self.warehouse_id)
        remark = '小心轻放'
        shipping_type = 'YTO'
        receiver, commodity = self.get_receiver_goods_message()
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
        content = content.replace('true', 'True').replace('false', 'False')
        print content
        #TODO
        """ file_html = open('express_html.html', 'w')
        # file_html.write(safe_eval(content).get('PrintTemplate'))
        # file_html.close()
        # pdfkit.from_file('express_html.html', 'express_pdf.pdf')
        # f = open('express_pdf.pdf', 'rb')"""
        self.express_menu = safe_eval(content).get('PrintTemplate')
        return True

    def encrypt_kdn(self, data, appkey):
        """
        数据加密
        """
        key = base64.b64encode(hashlib.md5("%s%s" % (data, appkey)).hexdigest(), altchars=None)
        return urllib.quote(key, safe='/')

