# -*- coding: utf-8-*-
from odoo import models, fields,api
from odoo.exceptions import UserError, ValidationError

# 微信企业号菜单
class wechat_agent_menu(models.Model):
    _inherit = 'wechat.agent.menu'

    def _get_agentid(self):
        """
        :return:  applcation 的application_id
        """
        print "++++++++++++++++"
        ir_model_data = self.env['ir.model.data'].sudo()
        wechat_application = self.env['wechat.application'].sudo()
        application_id = ir_model_data.xmlid_to_res_id('gooderp_weixin.weixin_gooderp_assistant_application')
        application = wechat_application.browse(application_id)
        if not application or not application.application_id:
            raise ValidationError(u'错误', u'无法获取到应用的agent_id')
        return application.application_id

    def _get_access_token(self):
        """
           :return:  applcation 的 access_token
           """
        ir_model_data = self.env['ir.model.data'].sudo()
        wechat_enterprise = self.env['wechat.enterprise'].sudo()
        enterprise_id = ir_model_data.xmlid_to_res_id('gooderp_weixin.weixin_gooderp_enterprise')
        enterprise = wechat_enterprise.browse(enterprise_id)
        if not enterprise or not enterprise.access_token:
            raise ValidationError(u'错误', u'无法获取到微信企业号的access_token')
        return enterprise.access_token
