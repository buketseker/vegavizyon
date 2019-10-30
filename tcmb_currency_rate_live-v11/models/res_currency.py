# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


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
            currency.inverse_rate = 1 / currency.rate or 0.0
            currency.inverse_banknot_buying_rate = 1 / currency.banknot_buying_rate or 0.0
            currency.inverse_forex_selling_rate = 1 / currency.forex_selling_rate or 0.0
            currency.inverse_forex_buying_rate = 1 / currency.forex_buying_rate or 0.0

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

    @api.multi
    def compute(self, from_amount, to_currency, round=True, rate_type="default"):
        if rate_type == "default":
            return super(Currency, self).compute(from_amount, to_currency, round)
        else:
            """ Convert `from_amount` from currency `self` to `to_currency`. """
            self, to_currency = self or to_currency, to_currency or self
            assert self, "compute from unknown currency"
            assert to_currency, "compute to unknown currency"
            # apply conversion rate
            if self == to_currency:
                to_amount = from_amount
            else:
                if rate_type == "Efektif Satış":
                    from_currency = self.with_env(self.env)
                    to_currency = to_currency.with_env(self.env)
                    rate = to_currency.rate / from_currency.rate
                elif rate_type == "Efektif Alış":
                    from_currency = self.with_env(self.env)
                    to_currency = to_currency.with_env(self.env)
                    rate = to_currency.rate / from_currency.banknot_buying_rate
                elif rate_type == "Döviz Alış":
                    from_currency = self.with_env(self.env)
                    to_currency = to_currency.with_env(self.env)
                    rate = to_currency.rate / from_currency.forex_buying_rate
                elif rate_type == "Döviz Satış":
                    from_currency = self.with_env(self.env)
                    to_currency = to_currency.with_env(self.env)
                    rate = to_currency.rate / from_currency.forex_selling_rate

                to_amount = from_amount * rate
            # apply rounding
            return to_currency.round(to_amount) if round else to_amount
