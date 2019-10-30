# -*- coding: utf-8 -*-

import requests
import logging
from datetime import datetime, timedelta
from lxml import etree

_logger = logging.getLogger(__name__)


class CurrencyHelper:
    _name = "Currency Helper"

    def get_rates_on_date(self, date, currency, company_currency="TRY"):
        # Syntax for receiving specific date
        # http://www.tcmb.gov.tr/kurlar/201905/08052019.xml
        date_found = datetime.strptime(date, "%Y-%m-%d")
        today = datetime.today().strftime("%Y-%m-%d")

        if today != date:
            new_month = date_found.month if len(str(date_found.month)) > 1 else "0" + str(date_found.month)
            request_url = "http://www.tcmb.gov.tr/kurlar/%s%s/%s.xml" % (
                date_found.year, new_month, date_found.strftime("%d%m%Y"))
        else:
            request_url = "http://www.tcmb.gov.tr/kurlar/today.xml"
        try:
            while requests.request('GET', request_url).status_code == 404:
                date_found = date_found - timedelta(days=1)
                new_month = date_found.month if len(str(date_found.month)) > 1 else "0" + str(date_found.month)
                request_url = "http://www.tcmb.gov.tr/kurlar/%s%s/%s.xml" % (
                    date_found.year, new_month, date_found.strftime("%d%m%Y"))

            response = requests.request('GET', request_url)
        except Exception as e:
            error_message = "Failed to get rate on date with url: %s. With following exception:%s" % (
                request_url, str(e))
            _logger.error(error_message)
            return False

        # Sanity Checks
        if response.status_code == 200:
            xmlstr = etree.fromstring(response.content)
            data = self.xml2json_from_elementtree(xmlstr)

            node = data
            currency_node = [(x['attrs']['CurrencyCode'], x['children'][6]['children'][0],
                              x['children'][5]['children'][0],
                              x['children'][4]['children'][0],
                              x['children'][3]['children'][0]) for x in node['children'] if
                             x['attrs']['CurrencyCode'] in [currency]]

            if not currency_node:
                _logger.warning("No currecy rates found for %s" % currency)
                return False

            base_currency_rates = [(x['attrs']['CurrencyCode'], x['children'][6]['children'][0],
                                    x['children'][5]['children'][0],
                                    x['children'][4]['children'][0],
                                    x['children'][3]['children'][0]) for x in node['children'] if
                                   x['attrs']['CurrencyCode'] == company_currency]

            base_currency_rate = len(base_currency_rates) and base_currency_rates[0][1] or 1
            rate = float(base_currency_rate) / float(currency_node[0][1])
            banknot_buying_rate = float(base_currency_rate) / float(currency_node[0][2])
            forex_selling_rate = float(base_currency_rate) / float(currency_node[0][3])
            forex_buying_rate = float(base_currency_rate) / float(currency_node[0][4])

            if data['attrs']:
                if data['attrs']['Date']:
                    found_date_on_xml = datetime.strptime(data['attrs']['Date'], '%m/%d/%Y').strftime('%Y-%m-%d')

            if len(currency_node):
                return {
                    "banknote_selling": rate,
                    "banknote_buying": banknot_buying_rate,
                    "forex_selling": forex_selling_rate,
                    "forex_buying": forex_buying_rate,
                    "date": found_date_on_xml
                }
            else:
                return False

    def xml2json_from_elementtree(self, el, preserve_whitespaces=False):
        """ xml2json-direct
        Simple and straightforward XML-to-JSON converter in Python
        New BSD Licensed
        http://code.google.com/p/xml2json-direct/
        """
        res = {}
        if el.tag[0] == "{":
            ns, name = el.tag.rsplit("}", 1)
            res["tag"] = name
            res["namespace"] = ns[1:]
        else:
            res["tag"] = el.tag
        res["attrs"] = {}
        for k, v in el.items():
            res["attrs"][k] = v
        kids = []
        if el.text and (preserve_whitespaces or el.text.strip() != ''):
            kids.append(el.text)
        for kid in el:
            kids.append(self.xml2json_from_elementtree(kid, preserve_whitespaces))
            if kid.tail and (preserve_whitespaces or kid.tail.strip() != ''):
                kids.append(kid.tail)
        res["children"] = kids
        return res

    def subtract_date(self, date1, date2):
        pass
