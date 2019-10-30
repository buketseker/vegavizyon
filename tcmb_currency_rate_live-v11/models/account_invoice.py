# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from .currency_helper import CurrencyHelper


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    currency_rate_type_id = fields.Many2one('res.currency.rate.type', string='Para Birimi Kur Tipi')

    currency_rate = fields.Float(string="Para Birimi Kuru", digits=(12, 6), default=1.0,
                                 compute='_compute_currency_inverse_rate',
                                 states={'draft': [('readonly', False)]})

    currency_inverse_rate = fields.Float(string="Para Birimi Kuru (inverse)", digits=(12, 6),
                                         compute='update_currency_rate', store=True, default=1.0,
                                         states={'draft': [('readonly', False)]})

    custom_rate = fields.Float(string='Custom Rate(Özel Kur Değeri)', digits=(12, 6))

    use_currency_rate = fields.Boolean(string="Use Currency Rate")

    use_custom_rate = fields.Boolean(string="Özel Kur")

    '''
    company_currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id',
                                          readonly=True)
    amount_total_company_currency = fields.Monetary("Toplam (Şirket Para Birimi)",
                                                    currency_field="company_currency_id",
                                                    readonly=True,
                                                    compute="_compute_amount_company")
    '''

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type', 'use_custom_rate', 'currency_rate_type_id', 'currency_rate')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            if not self.currency_rate_type_id and not self.use_custom_rate:
                amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
                amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
            elif self.use_custom_rate:
                if self.custom_rate == 0:
                    self.custom_rate = 1
                amount_total_company_signed = currency_id.round(self.amount_total * self.custom_rate)
                amount_untaxed_signed = currency_id.round(self.amount_untaxed * self.custom_rate)
            else:
                amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id,
                                                                  rate_type=self.currency_rate_type_id.name)
                amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id,
                                                            rate_type=self.currency_rate_type_id.name)

        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    @api.onchange('currency_id', 'company_currency_id')
    def onchange_currency_id(self):
        if not self.currency_id:
            self.use_currency_rate = False
        elif self.currency_id.id == self.company_currency_id.id:
            self.use_currency_rate = False
        else:
            self.use_currency_rate = True

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if vals.get('currency_rate'):
            res.update({
                'currency_inverse_rate': vals['currency_rate']
            })

        if vals.get('currency_id'):
            currency_id = self.env["res.currency"].search([('id', '=', vals.get('currency_id'))], limit=1)
            if currency_id:
                if res.company_id.currency_id.id != currency_id.id:
                    res.update({'use_currency_rate': True, 'currency_rate': 1 / currency_id.rate})
                    # Check values from SO if available
                    if vals.get('origin'):
                        so = self.env['sale.order'].search([('name', '=', vals.get('origin'))], limit=1)
                        if so:
                            if so.currency_id:
                                if so.currency_id.id == currency_id.id:
                                    if so.use_custom_rate:
                                        custom_rate = so.currency_rate
                                        res.update({'use_custom_rate': True, 'custom_rate': custom_rate})
                                if so.currency_rate_type_id:
                                    res.update({'currency_rate_type_id': so.currency_rate_type_id.id})

        return res

    @api.one
    @api.depends('currency_inverse_rate')
    def _compute_currency_inverse_rate(self):
        self.currency_rate = self.currency_inverse_rate

    @api.onchange('use_custom_rate')
    def onchange_custom_rate(self):
        if self.use_custom_rate:
            self.currency_rate_type_id = False
        else:
            pass

    # @api.onchange('currency_inverse_rate')
    # def compute_custom_rate(self):
    #     if self.currency_inverse_rate and self.use_custom_rate:
    #         self.custom_rate = self.currency_inverse_rate

    @api.multi
    def get_currencies(self, company_currency, currency, date_to_search):
        rate_helper = CurrencyHelper()
        currency_rates = rate_helper.get_rates_on_date(date_to_search, currency, company_currency)
        return currency_rates

    @api.multi
    @api.depends('currency_id', 'currency_rate_type_id', 'date_invoice', 'use_custom_rate', 'custom_rate')
    def update_currency_rate(self):
        for record in self:
            if record.currency_id:
                currency = record.currency_id
                rate_type = record.currency_rate_type_id
                currency_rate_obj = self.env['res.currency.rate']
                currency_rate_ids = currency_rate_obj.search([('currency_id', '=', currency.id)])
                if currency_rate_ids:
                    if record.date_invoice:
                        date_found = datetime.strptime(record.date_invoice, "%Y-%m-%d") - timedelta(days=1)
                        date_to_search = date_found.strftime("%Y-%m-%d")
                    else:
                        date_found = datetime.strptime(datetime.today().strftime("%Y-%m-%d"),
                                                       "%Y-%m-%d") - timedelta(days=1)
                        date_to_search = date_found.strftime("%Y-%m-%d")
                    search_domain = [('currency_id', '=', currency.id),
                                     ('name', '=', date_to_search)]
                    if record.company_id:
                        search_domain += [('company_id', '=', record.company_id.id)]
                    last_id = currency_rate_obj.search(search_domain, limit=1)

                    # Get Currency Rate
                    if not last_id:
                        company_currency = record.company_id.currency_id.name if (
                                record.company_id and record.company_id.currency_id) else "TRY"
                        currency_rates = record.get_currencies(company_currency, currency.name, date_to_search)
                        if currency_rates:
                            # perform another search cause rate_helper returns different date then sent one
                            search_domain = [('currency_id', '=', currency.id),
                                             ('name', '=', currency_rates["date"])]
                            if record.company_id:
                                search_domain += [('company_id', '=', record.company_id.id)]
                            last_id = currency_rate_obj.search(search_domain, limit=1)
                            if not last_id:
                                last_id = currency_rate_obj.create({'currency_id': currency.id,
                                                                    'rate': currency_rates["banknote_selling"],
                                                                    'banknot_buying_rate': currency_rates[
                                                                        "banknote_buying"],
                                                                    'forex_selling_rate': currency_rates[
                                                                        "forex_selling"],
                                                                    'forex_buying_rate': currency_rates["forex_buying"],
                                                                    'name': currency_rates["date"],
                                                                    'company_id': record.company_id.id})
                        else:
                            return
                    if record.currency_rate_type_id:
                        if rate_type.name == 'Efektif Satış':
                            if last_id.rate > 0.0:
                                record.currency_inverse_rate = 1 / last_id.rate
                        elif rate_type.name == 'Efektif Alış':
                            if last_id.banknot_buying_rate > 0.0:
                                record.currency_inverse_rate = 1 / last_id.banknot_buying_rate
                        elif rate_type.name == 'Döviz Satış':
                            if last_id.forex_selling_rate > 0.0:
                                record.currency_inverse_rate = 1 / last_id.forex_selling_rate
                        elif rate_type.name == 'Döviz Alış':
                            if last_id.forex_buying_rate > 0.0:
                                record.currency_inverse_rate = 1 / last_id.forex_buying_rate
                    elif record.use_custom_rate is False and not record.currency_rate_type_id:
                        if last_id.rate > 0.0:
                            record.currency_inverse_rate = 1 / last_id.rate
                    elif record.use_custom_rate and not record.currency_rate_type_id and record.custom_rate:
                        record.currency_inverse_rate = record.custom_rate
