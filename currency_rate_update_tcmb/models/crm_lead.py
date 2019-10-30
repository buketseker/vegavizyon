
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

from datetime import datetime


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    planned_revenue = fields.Float(compute='_compute_planned_revenue', store=True, track_visibility='always')
    planned_currency_rate = fields.Many2one('res.currency', string="Kur")
    expected_revenue = fields.Integer(string="Beklenen Ciro")

    @api.one
    @api.depends('planned_currency_rate', 'expected_revenue')
    def _compute_planned_revenue(self):
        expected_curr = self.expected_revenue or 0
        planned_curr = self. planned_currency_rate
        if expected_curr:
            currency_def = self.env['res.currency'].search([('id', '=', planned_curr.id)])
            if currency_def:
                currency_rate_ids = self.env['res.currency.rate'].search([('currency_id', '=', currency_def.id)])
                if currency_rate_ids:
                    last_curr_rate = currency_rate_ids and max(currency_rate_ids)
                    self.planned_revenue = int(self.expected_revenue) * 1 / last_curr_rate.rate



