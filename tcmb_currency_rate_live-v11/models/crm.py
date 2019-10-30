# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = "crm.lead"

    planned_revenue = fields.Float(compute='_compute_planned_revenue', store=True)
    beklenen_ciro_kuru = fields.Many2one('res.currency', string="Kur")
    beklenen_ciro = fields.Integer(string="Beklenen Ciro")

    @api.one
    @api.depends('planned_revenue', 'beklenen_ciro', 'beklenen_ciro_kuru')
    def _compute_planned_revenue(self):
        if self.beklenen_ciro_kuru:
            currency_def = self.env['res.currency'].search([('name', '=', self.beklenen_ciro_kuru.name)])
            if currency_def:
                currency_rate_ids = self.env['res.currency.rate'].search([('currency_id', '=', currency_def.id)])
                if currency_rate_ids:
                    last_id = currency_rate_ids and max(currency_rate_ids)
                    self.planned_revenue = int(self.beklenen_ciro) * 1 / last_id.rate
