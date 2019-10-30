# -*- coding: utf-8 -*-
{
    'name': "Total in Company Currency Module",

    'summary': """
        Total in company currency by currency rate type""",

    'description': """
        Total in company currency by choosen currency rate type in Account Invoice
    """,

    'author': "MechSoft",
    'website': "https://www.mechsoft.com.tr",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Currency',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'base_setup',
                'account',
                'account_invoicing',
                'currency_rate_update_tcmb'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],
}