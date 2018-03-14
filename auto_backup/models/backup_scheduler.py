# -*- coding: utf-8 -*-
##############################################################################
#
#    odoo, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2012-2015 Mrshelly@gmail.com  upgrade to 7.0
#    Copyright (C) 2014      JianJian@osbzr.com  upgrade to 8.0
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api
import xmlrpclib
import socket
import os
import time
import base64
import logging

import pytz
import datetime

from odoo import tools
from odoo import netsvc
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def execute(connector, method, *args):
    res = False
    try:
        res = getattr(connector, method)(*args)
    except socket.error, e:
        raise e
    return res


addons_path = '%s/DBbackups' % (os.environ.get('HOME', '')
                                or os.environ.get('HOMEPATH', ''))


class DbBackup(models.Model):
    _name = 'db.backup'
    _description = u'数据库自动备份'

    @api.model
    def get_db_list(self, host='localhost', port='8069'):
        uri = 'http://' + host + ':' + port
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
        db_list = execute(conn, 'list')
        return db_list

    host = fields.Char('Host', size=100, required='True', default='localhost')
    port = fields.Char('Port', size=10, required='True', default='8888')
    name = fields.Char('Database', size=100, required='True',
                       help='Database you want to schedule backups for')
    bkp_dir = fields.Char('Backup Directory', size=100,
                          help='Absolute path for storing the backups', required='True', default=addons_path)
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.constrains('name')
    def _check_db_exist(self):
        for rec in self.browse():
            db_list = self.get_db_list(rec.host, rec.port)
            if not rec.name in db_list:
                raise UserError('Error ! No such database exist.')

    @api.model
    def schedule_backup(self):
        confs = self.search([])
        master_pass = tools.config.get('admin_passwd', False)
        res_user_obj = self.env.get('res.users')
        if not master_pass:
            raise
        for rec in confs:
            db_list = self.get_db_list(rec.host, rec.port)
            # Get UTC time
            curtime = datetime.datetime.strptime(
                datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
            res_user_res = res_user_obj.browse(1)
            # user's partner timezone
            tz = pytz.timezone(
                res_user_res.tz) if res_user_res.tz else pytz.utc
            # Set to usre's localtime
            curtime = pytz.utc.localize(curtime).astimezone(tz)
            #curtime = curtime.astimezone(pytz.utc)

            if rec.name in db_list:
                try:
                    if not os.path.isdir(rec.bkp_dir):
                        os.makedirs(rec.bkp_dir)
                except:
                    raise
                bkp_file = '%s_%s.zip' % (
                    rec.name, curtime.strftime('%Y%m%d_%H_%M_%S'))
                file_path = os.path.join(rec.bkp_dir, bkp_file)
                uri = 'http://' + rec.host + ':' + rec.port
                conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
                bkp = ''
                try:
                    bkp = execute(conn, 'dump', master_pass, rec.name, 'zip')
                except:
                    _logger.info(
                        'backup', "Could'nt backup database %s. Bad database administrator password for server running at http://%s:%s" % (rec.name, rec.host, rec.port))
                    continue
                bkp = base64.decodestring(bkp)
                fp = open(file_path, 'wb')
                fp.write(bkp)
                fp.close()
            else:
                _logger.info('backup', "database %s doesn't exist on http://%s:%s" %
                             (rec.name, rec.host, rec.port))

        return True

    @api.model
    def schedule_backup_pgtool(self):
        confs = self.search([])
        master_pass = tools.config.get('admin_passwd', False)
        res_user_obj = self.env.get('res.users')
        if not master_pass:
            raise
        for rec in confs:
            db_list = self.get_db_list(rec.host, rec.port)
            # Get UTC time
            curtime = datetime.datetime.strptime(
                datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
            res_user_res = res_user_obj.browse()
            # user's partner timezone
            tz = pytz.timezone(
                res_user_res.tz) if res_user_res.tz else pytz.utc
            # Set to usre's localtime
            curtime = pytz.utc.localize(curtime).astimezone(tz)
            #curtime = curtime.astimezone(pytz.utc)

            if rec.name in db_list:
                try:
                    if not os.path.isdir(rec.bkp_dir):
                        os.makedirs(rec.bkp_dir)
                except:
                    raise
                bkp_file = '%s_%s.sql' % (
                    rec.name, curtime.strftime('%Y%m%d_%H_%M_%S'))
                file_path = os.path.join(rec.bkp_dir, bkp_file)
                bkp = ''
                try:
                    self._db_pg_dump(rec.name, file_path)
                except Exception, ex:
                    _logger.warn('auto_backup DUMP DB except: ' + str(ex))
                    continue
        return True

    @api.model
    def _db_pg_dump(self, db_name, db_filename):
        _logger.info('auto_backup DUMP DB!')
        pg_passwd = os.environ.get(
            'PGPASSWORD') or tools.config['db_password'] or False
        data = ''
        if not pg_passwd:
            _logger.error(
                'DUMP DB: %s failed! Please verify the configuration of the database password on the server. '
                'You may need to create a .pgpass file for authentication, or specify `db_password` in the '
                'server configuration file.\n %s', db_name, data)
            raise Exception, "Couldn't dump database"
        os.environ['PGPASSWORD'] = tools.config['db_password']
        cmd = ['pg_dump', '--format=c', '--no-owner']
        if tools.config['db_user']:
            cmd.append('--username=' + tools.config['db_user'])
        if tools.config['db_host']:
            cmd.append('--host=' + tools.config['db_host'])
        if tools.config['db_port']:
            cmd.append('--port=' + str(tools.config['db_port']))
        cmd.append('--file=' + db_filename)
        cmd.append(db_name)

        stdin, stdout = tools.exec_pg_command_pipe(*tuple(cmd))
        stdin.close()
        data = stdout.read()
        res = stdout.close()

        return base64.encodestring(data)
