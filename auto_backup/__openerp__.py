# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#    Copyright (C) 2013-09   Mr.Shelly (<mrshelly at hotmail.com>)
#    Copyright (C) 2014      JianJian@osbzr.com  upgrade to 8.0
#    Copyright (C) 2016      jeff@osbzr.com  upgrade to 10.0
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

{
    "name": "Database Auto-Backup",
    "version": "11.11",
    "author": "Tiny,MrShelly,JianJian",
    "website": "http://www.openerp.com",
    "category": "Generic Modules",
    "description": """The generic Open ERP Database Auto-Backup system enables the user to make configurations for the automatic backup of the database.
User simply requires to specify host & port under IP Configuration & database(on specified host running at specified port) and backup directory(in which all the backups of the specified database will be stored) under Database Configuration.

Automatic backup for all such configured databases under this can then be scheduled as follows:

1) Go to Administration / Configuration / Scheduler / Scheduled Actions
2) Schedule new action(create a new record)
3) Set 'Object' to 'db.backup' and 'Function' to 'schedule_backup' under page 'Technical Data'
4) Set other values as per your preference""",
    "depends": ['core'],
    "data": ["views/bkp_conf_view.xml",
              "security/ir.model.access.csv",
              "data/backup_data.xml"],
    'demo': [
        'data/backup_demo.xml',
    ],
    "installable": True
}
