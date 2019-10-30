# -*- coding: utf-8 -*-
{
    'name': "Currency Rate Update - TCMB",

    'description': """
        Import exchange rates from the Turkey TCMB Bank
    """,

    'author': "MechSoft",
    'website': "https://www.mechsoft.com.tr",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Currency',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_invoicing', 'currency_rate_update', 'crm'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'data/data.xml',
        'data/service_update_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}