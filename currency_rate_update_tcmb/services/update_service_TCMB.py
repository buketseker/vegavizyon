# -*- coding: utf-8 -*-


from lxml import etree
import json
from dateutil.relativedelta import relativedelta
import requests
import urllib
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import xml2json_from_elementtree
from odoo.exceptions import UserError
from odoo.tools.translate import _

from odoo.addons.currency_rate_update.services.currency_getter_interface import CurrencyGetterInterface

import logging
_logger = logging.getLogger(__name__)


class TCMBGetter(CurrencyGetterInterface):
    """
    Türkiye Cumhuriyeti Merkez Bankası Döviz Kuru İmplementasyonu
    """
    code = 'TCMB'
    name = 'TCMB Merkez Bankası'
    supported_currency_array = [
        "USD", "AUD", "DKK", "EUR", "GBP", "CHF", "SEK",
        "CAD", "KWD", "NOK", "SAR", "JPY", "BGN", "RON",
        "RUB", "IRR", "CNY", "PKR", "QAR", 'TRY']

    def rate_retrieve(self, node, curr):
        res = {}
        base_currency_rates = [(x['attrs']['CurrencyCode'],
                                x['children'][6]['children'][0],
                                x['children'][5]['children'][0],
                                x['children'][4]['children'][0],
                                x['children'][3]['children'][0])
                               for x in node['children'] if x['attrs']['CurrencyCode'] == curr.upper()]

        res['rate_currency'] = len(base_currency_rates) and base_currency_rates[0][1] or 1

        res['banknot_buying_currency'] = len(base_currency_rates) and base_currency_rates[0][2] or 1
        res['forex_selling_currency'] = len(base_currency_rates) and base_currency_rates[0][3] or 1
        res['forex_buying_currency'] = len(base_currency_rates) and base_currency_rates[0][4] or 1

        return res

    def check_date(self, node, max_delta_days):
        rate_date = node['attrs']['Tarih']
        rate_date_datetime = datetime.strptime(rate_date, '%d.%m.%Y') + timedelta(days=1)
        self.check_rate_date(rate_date_datetime, max_delta_days)

    def get_updated_currency(self, currency_array, main_currency, max_delta_days):
        request_url = "http://www.tcmb.gov.tr/kurlar/today.xml"

        if main_currency in currency_array:
            currency_array.remove(main_currency)

        _logger.info('TCMB Currency Rate Service: connecting..')

        #Currency = self.env['res.currency']
        # CurrencyRate = self.env['res.currency.rate'] => Bu object burada çağırılmayacak.

        #currencies = Currency.search([]) => currencies yerine parametreden gelen currency_array kullanılacak.
        #currencies = [curr.name for curr in currencies]

        try:
            parse_url = requests.request('GET', request_url)
            _logger.info("TCMB sent a valid url")
        except:
            return False

        xmlstr = etree.fromstring(parse_url.content)
        data = xml2json_from_elementtree(xmlstr)
        if data:
            _logger.info("TCMB sent a valid data")

        node = data
        self.check_date(node, max_delta_days)
        self.supported_currency_array.append('EUR')
        _logger.info('Supported currencies = %s', self.supported_currency_array)
        self.validate_cur(main_currency)

        if main_currency != 'TRY':
            main_currency_data = self.rate_retrieve(node, main_currency)

        for curr in currency_array:
            self.validate_cur(curr)
            if curr == 'TRY':
                rate = 1 / main_currency_data['rate_currency']
                rate_bb = 1 / main_currency_data['banknot_buying_currency']
                rate_fs = 1 / main_currency_data['forex_selling_currency']
                rate_fb = 1 / main_currency_data['forex_buying_currency']
            else:
                currency_data = self.rate_retrieve(node, curr)
                if main_currency == 'TRY':
                    rate = currency_data['rate_currency']
                    rate_bb = currency_data['banknot_buying_currency']
                    rate_fs = currency_data['forex_selling_currency']
                    rate_fb = currency_data['forex_buying_currency']
                else:
                    rate = currency_data['rate_currency'] / main_currency_data['rate_currency']
                    rate_bb = currency_data['banknot_buying_currency'] / main_currency_data['banknot_buying_currency']
                    rate_fs = currency_data['forex_selling_currency'] / main_currency_data['forex_selling_currency']
                    rate_fb = currency_data['forex_buying_currency'] / main_currency_data['forex_buying_currency']

            # Nested Dictionary for TCMB Döviz Alış, Döviz Satış, Efektif Alış, Efektif Satış
            self.updated_currency[curr] = {}
            self.updated_currency[curr]['rate'] = rate
            self.updated_currency[curr]['rate_bb'] = rate_bb
            self.updated_currency[curr]['rate_fs'] = rate_fs
            self.updated_currency[curr]['rate_fb'] = rate_fb
            _logger.info(
                'Kur oranlari alindi: 1 %s = %s %s (Gecerli Kur)' % (main_currency, rate, curr)
            )
        return self.updated_currency, self.log_info



























