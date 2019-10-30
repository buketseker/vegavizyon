# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

from datetime import datetime


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    currency_rate_type_id = fields.Many2one('res.currency.rate.type', string='Para Birimi Kur Tipi')

    currency_rate_type_id_virtual = fields.Many2one('res.currency.rate.type', string="Para Birimi Kur Tipi(Virtual)")

    currency_rate = fields.Float(string="Para Birimi Kuru", digits=(12, 4), default=1.0,
                                 compute='_compute_currency_inverse_rate')

    currency_inverse_rate = fields.Float(string="Para Birimi Kuru (inverse)", digits=(12, 4),
                                         compute='update_currency_rate', store=True, default=1.0)

    custom_rate = fields.Float(string='Custom Rate(Özel Kur Değeri)', digits=(12, 4))

    use_currency_rate = fields.Boolean(string="Use Currency Rate", compute='onchange_currency_id')

    use_custom_rate = fields.Boolean(string="Özel Kur")

    @api.multi
    @api.depends('currency_id', 'company_currency_id')
    def onchange_currency_id(self):
        for invoice in self:
            if not invoice.currency_id:
                invoice.use_currency_rate = False
            elif invoice.currency_id.id == invoice.company_currency_id.id:
                invoice.use_currency_rate = False
            else:
                invoice.use_currency_rate = True

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if vals.get('currency_rate'):
            res.update({
                'currency_inverse_rate': vals['currency_rate']
            })
        return res

    # tODO: trying onchange currency
    @api.onchange('currency_id')
    def onchange_currency_id_value(self):
        if self.currency_id and self.currency_id.id != self.env.user.company_id.currency_id.id and self.currency_rate_type_id.id is False:
            rate_type = self.env['res.currency.rate.type'].search([('name', '=', 'Efektif Satış')])
            self.currency_rate_type_id_virtual = rate_type
            self.currency_rate_type_id = self.currency_rate_type_id_virtual

    @api.one
    @api.depends('currency_inverse_rate')
    def _compute_currency_inverse_rate(self):
        self.currency_rate = self.currency_inverse_rate

    @api.onchange('use_custom_rate')
    def onchange_custom_rate(self):
        if self.use_custom_rate:
            self.currency_rate_type_id = False
        else:
            self.onchange_currency_id_value()

    @api.multi
    @api.depends('currency_id', 'currency_rate_type_id', 'date_invoice', 'use_custom_rate', 'custom_rate')
    def update_currency_rate(self):
        for record in self:
            if record.currency_rate_type_id:
                currency = record.currency_id
                rate_type = record.currency_rate_type_id
                currency_rate_obj = self.env['res.currency.rate']
                expected_currency = self.env['res.currency'].search([('id', '=', currency.id)])
                currencyRateIds = currency_rate_obj.search([('currency_id', '=', expected_currency.id)])
                if currencyRateIds:
                    last_id = max(currencyRateIds)
                    if len(currencyRateIds) > 1:
                        last_id = currencyRateIds and currencyRateIds[1]
                    if record.date_invoice:
                        today = datetime.now().strftime("%Y-%m-%d")
                        if record.date_invoice != today:
                            rate_by_date = currency_rate_obj.search([('currency_id', '=', expected_currency.id),
                                                                     ('name', '=', record.date_invoice)], limit=1)
                            last_id = currency_rate_obj.search([('currency_id', '=', expected_currency.id),
                                                                ('id', '<', rate_by_date.id)], order="id desc", limit=1)
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
                currency = record.currency_id
                currency_rate_obj = self.env['res.currency.rate']
                expected_currency = record.env['res.currency'].search([('id', '=', currency.id)])
                currencyRateIds = currency_rate_obj.search([('currency_id', '=', expected_currency.id)])
                if currencyRateIds:
                    last_id = max(currencyRateIds)
                    if len(currencyRateIds) > 1:
                        last_id = currencyRateIds and currencyRateIds[1]
                    if record.date_invoice:
                        today = datetime.now().strftime("%Y-%m-%d")
                        if record.date_invoice != today:
                            rate_by_date = currency_rate_obj.search([('currency_id', '=', expected_currency.id),
                                                                     ('name', '=', record.date_invoice)], limit=1)
                            last_id = currency_rate_obj.search([('currency_id', '=', expected_currency.id),
                                                                ('id', '<', rate_by_date.id)], order="id desc", limit=1)
                    if last_id.rate > 0.0:
                        record.currency_inverse_rate = 1 / last_id.rate

            elif record.use_custom_rate and not record.currency_rate_type_id and record.custom_rate:
                record.currency_inverse_rate = record.custom_rate









