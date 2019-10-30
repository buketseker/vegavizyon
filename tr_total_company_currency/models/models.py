# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    is_multi_currency = fields.Boolean(string="Company with multi currency")

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type', 'currency_rate_type_id', 'currency_inverse_rate')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            temp_signed = 0.0
            # TODO: company currency => will send to compute method with the new parameter called rate_type_id -> comp.
            if self.currency_rate_type_id and not self.use_custom_rate:
                for line in self.invoice_line_ids:
                    temp_signed += currency_id.compute(line.price_subtotal, self.company_id.currency_id,
                                                       rate_type=self.currency_rate_type_id, date=self.date_invoice)
                amount_total_company_signed = temp_signed
                if self.tax_line_ids and self.amount_tax > 0.0:
                    amount_total_company_signed += currency_id.compute(self.amount_tax, self.company_id.currency_id,
                                                                       rate_type=self.currency_rate_type_id, date=self.date_invoice)
            elif self.use_custom_rate and not self.currency_rate_type_id:
                for line in self.invoice_line_ids:
                    temp_signed += currency_id.compute(line.price_subtotal, self.company_id.currency_id,date=self.date_invoice,
                                                       use_custom_rate=self.use_custom_rate, custom_rate=self.currency_inverse_rate)
                amount_total_company_signed = temp_signed
                if self.tax_line_ids and self.amount_tax > 0.0:
                    amount_total_company_signed += currency_id.compute(self.amount_tax, self.company_id.currency_id,
                                                                      date=self.date_invoice, use_custom_rate=self.use_custom_rate, custom_rate=self.currency_inverse_rate)
            else:
                amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
                amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)

        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    """
    VERY IMPORTANT !!!
    This method is overrided for send rate_type(Efektif Alış,Satış vs..)
    """
    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(
                    date=self._get_currency_rate_date() or fields.Date.context_today(self))
                if not (line.get('cu'
                                 'rrency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = currency.round(line['price'])
                    # ------- Extra Codes -------
                    if self.currency_rate_type_id:
                        rate_type = self.currency_rate_type_id

                        line['price'] = currency.compute(line['price'], company_currency, rate_type=rate_type,
                                                         date=self.date_invoice)  # send rate_type to compute method
                    else:
                        line['price'] = currency.compute(line['price'], company_currency, date=self.date_invoice,
                                                         use_custom_rate=self.use_custom_rate, custom_rate=self.currency_inverse_rate) # send custom_rate to compute method
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, rate_type=False, date=False):
        from_currency = from_currency.with_env(self.env)
        to_currency = to_currency.with_env(self.env)

        # This operations is done for sale
        fr_is_same_currency = False
        company_currency = self.env.user.company_id.currency_id
        if from_currency.id == company_currency.id:
            # TODO : swap from 'from_currency' to 'to_currency'
            fr_is_same_currency = True
            temp = from_currency
            from_currency = to_currency
            to_currency = temp

        # TODO : the calculation to be done by date_invoice again -> completed
        if date:
            rate_by_date = self.env['res.currency.rate'].search([('currency_id', '=', from_currency.id), ('name', '<=', date)])
            from_currency.rate_ids = rate_by_date
        # TODO: calculation by rate type -> completed
        if rate_type:
            if rate_type.name == "Döviz Alış":
                return to_currency.forex_buying_rate / from_currency.rate_ids[1].forex_buying_rate if len(from_currency.rate_ids) > 1 else to_currency.rate / max(from_currency.rate_ids).forex_buying_rate
            elif rate_type.name == "Döviz Satış":
                return to_currency.forex_selling_rate / from_currency.rate_ids[1].forex_selling_rate if len(from_currency.rate_ids) > 1 else to_currency.rate / max(from_currency.rate_ids).forex_selling_rate
            elif rate_type.name == "Efektif Alış":
                return to_currency.banknot_buying_rate / from_currency.rate_ids[1].banknot_buying_rate if len(from_currency.rate_ids) > 1 else to_currency.rate / max(from_currency.rate_ids).banknot_buying_rate
            else:
                return to_currency.rate / from_currency.rate_ids[1].rate if len(from_currency.rate_ids) > 1 else to_currency.rate / max(from_currency.rate_ids).rate

        if fr_is_same_currency is True and to_currency.id == company_currency.id:
            return from_currency.rate / to_currency.rate_ids[1].rate if len(to_currency.rate_ids) > 1 else from_currency.rate / max(to_currency.rate_ids).rate
            # return from_currency.rate * 1
        return to_currency.rate / from_currency.rate_ids[1].rate if len(from_currency.rate_ids) > 1 else to_currency.rate / max(from_currency.rate_ids).rate

    # TODO: company_currency => method parameter count to be increased -> completed
    @api.multi
    def compute(self, from_amount, to_currency, round=True, rate_type=False, date=False, **kwargs):
        """ Convert `from_amount` from currency `self` to `to_currency`. """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "compute from unknown currency"
        assert to_currency, "compute to unknown currency"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            if "use_custom_rate" in kwargs and "custom_rate" in kwargs:
                to_amount = from_amount * kwargs['custom_rate']
            else:
                to_amount = from_amount * self._get_conversion_rate(self, to_currency, rate_type=rate_type, date=date) # method called with extra parameter
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount

