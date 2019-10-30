# -*- coding: utf-8 -*-

from lxml import etree
import requests
from odoo import api, fields, models
from odoo.tools.translate import _
from datetime import datetime
from .currency_helper import CurrencyHelper
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    currency_provider = fields.Selection(selection_add=[('tcmb', 'TCMB')], default='tcmb', string='Service Provider')

    @api.multi
    def update_currency_rates(self):
        ''' This method is used to update all currencies given by the provider. Depending on the selection call _update_currency_ecb _update_currency_yahoo. '''
        res = True
        all_good = True
        for company in self:
            if company.currency_provider == 'yahoo':
                _logger.warning("Call to the discontinued Yahoo currency rate web service.")
            elif company.currency_provider == 'ecb':
                res = company._update_currency_ecb()
            elif company.currency_provider == 'fta':
                res = company._update_currency_fta()
            elif company.currency_provider == 'banxico':
                res = company._update_currency_banxico()
            elif company.currency_provider == 'tcmb':
                res = company._update_currency_tcmb()
            if not res:
                all_good = False
                _logger.warning(_(
                    'Unable to connect to the online exchange rate platform %s. The web service may be temporary down.') % company.currency_provider)
            elif company.currency_provider:
                company.last_currency_sync_date = fields.Date.today()
        return all_good

    @api.multi
    def _update_currency_tcmb(self):

        currency_rate_obj = self.env['res.currency.rate']

        currencies = self.env['res.currency'].search([])
        # currencies = [x.name for x in currencies]

        today = datetime.today().strftime("%Y-%m-%d")

        for company in self:
            for currency in currencies:
                rate_helper = CurrencyHelper()
                rates = rate_helper.get_rates_on_date(today, currency.name, company.currency_id.name)
                if rates:
                    # perform another search cause rate_helper returns different date then sent one
                    search_domain = [('currency_id', '=', currency.id),
                                     ('name', '=', rates["date"]), ('company_id', '=', company.id)]

                    last_id = currency_rate_obj.search(search_domain, limit=1)
                    if not last_id:
                        try:
                            currency_rate_obj.create({'currency_id': currency.id,
                                                      'rate': rates["banknote_selling"],
                                                      'banknot_buying_rate': rates[
                                                          "banknote_buying"],
                                                      'forex_selling_rate': rates[
                                                          "forex_selling"],
                                                      'forex_buying_rate': rates["forex_buying"],
                                                      'name': rates["date"],
                                                      'company_id': company.id})
                        except Exception as e:
                            _logger.warning("An error occured while creating currency rate skipping: %s" % str(e))
                            continue

        return True
