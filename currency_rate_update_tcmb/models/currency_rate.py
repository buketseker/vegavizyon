# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

from datetime import datetime


class CurrencyRateType(models.Model):
    _name = 'res.currency.rate.type'
    _description = 'Para Birimi Kur Tipi'

    name = fields.Char(string='Kur Tipi')


class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    banknot_buying_rate = fields.Float(digits=(12, 6), string="Efektif Alış")
    forex_selling_rate = fields.Float(digits=(12, 6), string="Döviz Satış")
    forex_buying_rate = fields.Float(digits=(12, 6), string="Döviz Alış")


class Currency(models.Model):
    _inherit = 'res.currency'

    rate = fields.Float(compute='_compute_current_rate', string='Efektif Satış', digits=(12, 6),
                        help='The rate of the currency to the currency of rate 1.')
    banknot_buying_rate = fields.Float(digits=(12, 6), string="Efektif Alış", compute='compute_banknot_buying_rate')
    forex_selling_rate = fields.Float(digits=(12, 6), string="Döviz Satış", compute='compute_forex_selling_rate')
    forex_buying_rate = fields.Float(digits=(12, 6), string="Döviz Alış", compute='compute_forex_buying_rate')

    inverse_rate = fields.Float(compute="compute_inverse_rate_values", string="Geçerli Ters Kur",
                                digits=(12, 6))
    inverse_banknot_buying_rate = fields.Float(compute="compute_inverse_rate_values", string="Ters Efektif Alış Kuru",
                                               digits=(12, 6))
    inverse_forex_selling_rate = fields.Float(compute="compute_inverse_rate_values", string="Ters Döviz Satış Kuru",
                                              digits=(12, 6))
    inverse_forex_buying_rate = fields.Float(compute="compute_inverse_rate_values", string="Ters Döviz Alış Kuru",
                                             digits=(12, 6))

    @api.multi
    @api.depends('rate', 'banknot_buying_rate', 'forex_selling_rate', 'forex_buying_rate')
    def compute_inverse_rate_values(self):
        for currency in self:
            if currency.rate > 0:
                currency.inverse_rate = 1 / currency.rate
            if currency.banknot_buying_rate > 0:
                currency.inverse_banknot_buying_rate = 1 / currency.banknot_buying_rate
            if currency.forex_selling_rate > 0:
                currency.inverse_forex_selling_rate = 1 / currency.forex_selling_rate
            if currency.forex_buying_rate > 0:
                currency.inverse_forex_buying_rate = 1 / currency.forex_buying_rate

    @api.multi
    @api.depends('rate_ids.rate')
    def compute_banknot_buying_rate(self):
        date = self._context.get('date') or fields.Date.today()
        company_id = self._context.get('company_id') or self.env['res.users']._get_company().id
        query = """SELECT c.id, (SELECT r.banknot_buying_rate FROM res_currency_rate r
                                              WHERE r.currency_id = c.id AND r.name <= %s
                                                AND (r.company_id IS NULL OR r.company_id = %s)
                                           ORDER BY r.company_id, r.name DESC
                                              LIMIT 1) AS banknot_buying_rate
                               FROM res_currency c
                               WHERE c.id IN %s"""
        self._cr.execute(query, (date, company_id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        for currency in self:
            currency.banknot_buying_rate = currency_rates.get(currency.id) or 1.0

    @api.multi
    @api.depends('rate_ids.rate')
    def compute_forex_selling_rate(self):
        date = self._context.get('date') or fields.Date.today()
        company_id = self._context.get('company_id') or self.env['res.users']._get_company().id
        query = """SELECT c.id, (SELECT r.forex_selling_rate FROM res_currency_rate r
                                              WHERE r.currency_id = c.id AND r.name <= %s
                                                AND (r.company_id IS NULL OR r.company_id = %s)
                                           ORDER BY r.company_id, r.name DESC
                                              LIMIT 1) AS forex_selling_rate
                               FROM res_currency c
                               WHERE c.id IN %s"""
        self._cr.execute(query, (date, company_id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        for currency in self:
            currency.forex_selling_rate = currency_rates.get(currency.id) or 1.0

    @api.multi
    @api.depends('rate_ids.rate')
    def compute_forex_buying_rate(self):
        date = self._context.get('date') or fields.Date.today()
        company_id = self._context.get('company_id') or self.env['res.users']._get_company().id
        query = """SELECT c.id, (SELECT r.forex_buying_rate FROM res_currency_rate r
                                              WHERE r.currency_id = c.id AND r.name <= %s
                                                AND (r.company_id IS NULL OR r.company_id = %s)
                                           ORDER BY r.company_id, r.name DESC
                                              LIMIT 1) AS forex_buying_rate
                               FROM res_currency c
                               WHERE c.id IN %s"""
        self._cr.execute(query, (date, company_id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        for currency in self:
            currency.forex_buying_rate = currency_rates.get(currency.id) or 1.0