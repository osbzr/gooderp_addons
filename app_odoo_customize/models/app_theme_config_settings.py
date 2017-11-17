# -*- coding: utf-8 -*-

import logging

from openerp import api, fields, models, _

_logger = logging.getLogger(__name__)


class AppThemeConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'app.theme.config.settings'

    _description = u"App Odoo Customize settings"
    app_system_name = fields.Char('System Name', help=u"Setup System Name,which replace Odoo")
    app_show_lang = fields.Boolean('Show Quick Language Switcher',
                                   help=u"When enable,User can quick switch language in user menu")
    app_show_debug = fields.Boolean('Show Quick Debug', help=u"When enable,everyone login can see the debug menu")
    app_show_documentation = fields.Boolean('Show Documentation', help=u"When enable,User can visit user manual")
    app_show_documentation_dev = fields.Boolean('Show Developer Documentation',
                                                help=u"When enable,User can visit development documentation")
    app_show_support = fields.Boolean('Show Support', help=u"When enable,User can vist your support site")
    app_show_account = fields.Boolean('Show My Account', help=u"When enable,User can login to your website")
    app_show_enterprise = fields.Boolean('Show Enterprise Tag', help=u"Uncheck to hide the Enterprise tag")
    app_show_share = fields.Boolean('Show Share Dashboard', help=u"Uncheck to hide the Odoo Share Dashboard")
    app_show_poweredby = fields.Boolean('Show Powered by Odoo', help=u"Uncheck to hide the Powered by text")

    app_documentation_url = fields.Char('Documentation Url')
    app_documentation_dev_url = fields.Char('Developer Documentation Url')
    app_support_url = fields.Char('Support Url')
    app_account_title = fields.Char('My Odoo.com Account Title')
    app_account_url = fields.Char('My Odoo.com Account Url')

    @api.model
    def get_default_all(self, fields):
        ir_config = self.env['ir.config_parameter']
        app_system_name = ir_config.get_param('app_system_name', default='odooApp')

        app_show_lang = True if ir_config.get_param('app_show_lang') == "True" else False
        app_show_debug = True if ir_config.get_param('app_show_debug') == "True" else False
        app_show_documentation = True if ir_config.get_param('app_show_documentation') == "True" else False
        app_show_documentation_dev = True if ir_config.get_param('app_show_documentation_dev') == "True" else False
        app_show_support = True if ir_config.get_param('app_show_support') == "True" else False
        app_show_account = True if ir_config.get_param('app_show_account') == "True" else False
        app_show_enterprise = True if ir_config.get_param('app_show_enterprise') == "True" else False
        app_show_share = True if ir_config.get_param('app_show_share') == "True" else False
        app_show_poweredby = True if ir_config.get_param('app_show_poweredby') == "True" else False

        app_documentation_url = ir_config.get_param('app_documentation_url',
                                                    default='http://www.sunpop.cn/documentation/user/10.0/en/index.html')
        app_documentation_dev_url = ir_config.get_param('app_documentation_dev_url',
                                                        default='http://www.sunpop.cn/documentation/10.0/index.html')
        app_support_url = ir_config.get_param('app_support_url', default='http://www.sunpop.cn/trial/')
        app_account_title = ir_config.get_param('app_account_title', default='My Online Account')
        app_account_url = ir_config.get_param('app_account_url', default='http://www.sunpop.cn/my-account/')
        return dict(
            app_system_name=app_system_name,
            app_show_lang=app_show_lang,
            app_show_debug=app_show_debug,
            app_show_documentation=app_show_documentation,
            app_show_documentation_dev=app_show_documentation_dev,
            app_show_support=app_show_support,
            app_show_account=app_show_account,
            app_show_enterprise=app_show_enterprise,
            app_show_share=app_show_share,
            app_show_poweredby=app_show_poweredby,
            app_documentation_url=app_documentation_url,
            app_documentation_dev_url=app_documentation_dev_url,
            app_support_url=app_support_url,
            app_account_title=app_account_title,
            app_account_url=app_account_url
        )

    @api.multi
    def set_default_all(self):
        self.ensure_one()
        ir_config = self.env['ir.config_parameter']
        ir_config.set_param("app_system_name", self.app_system_name or "")
        ir_config.set_param("app_show_lang", self.app_show_lang or "False")
        ir_config.set_param("app_show_debug", self.app_show_debug or "False")
        ir_config.set_param("app_show_documentation", self.app_show_documentation or "False")
        ir_config.set_param("app_show_documentation_dev", self.app_show_documentation_dev or "False")
        ir_config.set_param("app_show_support", self.app_show_support or "False")
        ir_config.set_param("app_show_account", self.app_show_account or "False")
        ir_config.set_param("app_show_enterprise", self.app_show_enterprise or "False")
        ir_config.set_param("app_show_share", self.app_show_share or "False")
        ir_config.set_param("app_show_poweredby", self.app_show_poweredby or "False")

        ir_config.set_param("app_documentation_url",
                            self.app_documentation_url or "http://www.sunpop.cn/documentation/user/10.0/en/index.html")
        ir_config.set_param("app_documentation_dev_url",
                            self.app_documentation_dev_url or "http://www.sunpop.cn/documentation/10.0/index.html")
        ir_config.set_param("app_support_url", self.app_support_url or "http://www.sunpop.cn/trial/")
        ir_config.set_param("app_account_title", self.app_account_title or "My Online Account")
        ir_config.set_param("app_account_url", self.app_account_url or "http://www.sunpop.cn/my-account/")

        return True
