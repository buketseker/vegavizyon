# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from .currency_helper import CurrencyHelper


class SaleOrder(models.Model):
    _inherit = "sale.order"

    use_currency_rate = fields.Boolean(string="Use Currency Rate")
    currency_rate_type_id = fields.Many2one('res.currency.rate.type', string='Para Birimi Kur Tipi')
    use_custom_rate = fields.Boolean(string="Özel Kur")
    custom_rate = fields.Float(string='Custom Rate(Özel Kur Değeri)', digits=(12, 6))
    currency_rate = fields.Float(string="Para Birimi Kuru", digits=(12, 6), default=1.0,
                                 compute='update_currency_rate',
                                 inverse='_set_custom_rate',
                                 store=True,
                                 states={'draft': [('readonly', False)]})
    company_currency_id = fields.Many2one('res.currency', 'Company Currency', related='company_id.currency_id', readonly=True)
    amount_untaxed_signed = fields.Monetary(string='Vergiler Hariç Tutar',
                                            currency_field='company_currency_id', store=True,
                                            readonly=True, compute='compute_amount_company_signed')
    amount_total_company_signed = fields.Monetary(string='Toplam (Şirket Para Birimi)',
                                                  currency_field='company_currency_id', store=True,
                                                  readonly=True, compute='compute_amount_company_signed',
                                                  help="Total amount in the currency of the company, negative for credit notes.")

    @api.onchange('currency_id')
    def _onchange_pricelist(self):
        if self.currency_id:
            if self.currency_id.id != self.company_id.currency_id.id:
                self.use_currency_rate = True
                return
        self.use_currency_rate = False

    @api.multi
    def _set_custom_rate(self):
        if self.currency_rate:
            self.custom_rate = self.currency_rate

    @api.multi
    def get_currencies(self, company_currency, currency, date_to_search):
        rate_helper = CurrencyHelper()
        currency_rates = rate_helper.get_rates_on_date(date_to_search, currency, company_currency)
        return currency_rates

    @api.multi
    @api.depends('amount_total', 'currency_rate')
    def compute_amount_company_signed(self):
        for record in self:
            if record.currency_id:
                if not record.use_custom_rate:
                    currency_id = record.currency_id
                    if not record.currency_rate_type_id:
                        record.amount_total_company_signed = currency_id.compute(record.amount_total,
                                                                                 record.company_id.currency_id)
                        record.amount_untaxed_signed = currency_id.compute(record.amount_untaxed,
                                                                           record.company_id.currency_id)
                    else:
                        record.amount_total_company_signed = currency_id.compute(record.amount_total,
                                                                                 record.company_id.currency_id,
                                                                                 rate_type=record.currency_rate_type_id.name)
                        record.amount_untaxed_signed = currency_id.compute(record.amount_untaxed,
                                                                           record.company_id.currency_id,
                                                                           rate_type=record.currency_rate_type_id.name)
                else:
                    record.amount_total_company_signed = record.amount_total * record.currency_rate
                    record.amount_untaxed_signed = record.amount_untaxed * record.currency_rate
            else:
                record.amount_total_company_signed = record.amount_total
                record.amount_untaxed_signed = record.amount_untaxed

    @api.multi
    @api.depends('use_custom_rate', 'currency_rate_type_id', 'date_order', 'currency_id')
    def update_currency_rate(self):
        for record in self:
            if record.currency_id:
                if record.currency_id.id != record.company_id.currency_id.id:
                    record.use_currency_rate = True
                else:
                    record.use_currency_rate = False
            else:
                record.use_currency_rate = False

            if not record.use_custom_rate and record.use_currency_rate:
                currency_rate_obj = self.env['res.currency.rate']
                date_found = datetime.strptime(datetime.today().strftime("%Y-%m-%d"),
                                               "%Y-%m-%d") - timedelta(days=1)
                date_to_search = date_found.strftime("%Y-%m-%d")
                if record.date_order:
                    date_found = datetime.strptime(record.date_order, "%Y-%m-%d %H:%M:%S") - timedelta(days=1)
                    date_to_search = date_found.strftime("%Y-%m-%d")
                search_domain = [('currency_id', '=', record.currency_id.id),
                                 ('name', '=', date_to_search)]
                if record.company_id:
                    search_domain += [('company_id', '=', record.company_id.id)]
                last_id = currency_rate_obj.search(search_domain, limit=1)
                # Get Currency Rate
                if not last_id:
                    company_currency = record.company_id.currency_id.name if (
                            record.company_id and record.company_id.currency_id) else "TRY"
                    currency_rates = record.get_currencies(company_currency, record.currency_id.name, date_to_search)
                    if currency_rates:
                        # perform another search cause rate_helper returns different date then sent one
                        search_domain = [('currency_id', '=', record.currency_id.id),
                                         ('name', '=', currency_rates["date"])]
                        if record.company_id:
                            search_domain += [('company_id', '=', record.company_id.id)]
                        last_id = currency_rate_obj.search(search_domain, limit=1)
                        if not last_id:
                            last_id = currency_rate_obj.create({'currency_id': record.currency_id.id,
                                                                'rate': currency_rates["banknote_selling"],
                                                                'banknot_buying_rate': currency_rates[
                                                                    "banknote_buying"],
                                                                'forex_selling_rate': currency_rates[
                                                                    "forex_selling"],
                                                                'forex_buying_rate': currency_rates["forex_buying"],
                                                                'name': currency_rates["date"],
                                                                'company_id': record.company_id.id})

                if record.currency_rate_type_id:
                    rate_type = record.currency_rate_type_id
                    if rate_type.name == 'Efektif Satış':
                        if last_id.rate > 0.0:
                            record.currency_rate = 1 / last_id.rate
                    elif rate_type.name == 'Efektif Alış':
                        if last_id.banknot_buying_rate > 0.0:
                            record.currency_rate = 1 / last_id.banknot_buying_rate
                    elif rate_type.name == 'Döviz Satış':
                        if last_id.forex_selling_rate > 0.0:
                            record.currency_rate = 1 / last_id.forex_selling_rate
                    elif rate_type.name == 'Döviz Alış':
                        if last_id.forex_buying_rate > 0.0:
                            record.currency_rate = 1 / last_id.forex_buying_rate
                else:
                    if last_id.rate > 0.0:
                        record.currency_rate = 1 / last_id.rate
            else:
                if not record.currency_rate:
                    record.currency_rate = 1.0
