from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        multi_currency_configuration = ICP.get_param('base_setup.group_multi_currency')
        res.update(
            multi_currency_configuration=multi_currency_configuration
        )
        _logger.info('Company configuration is loading')
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        _logger.info('Company multi currency configurations is setting')
        ICP = self.env['ir.config_parameter']
        ICP.set_param('base_setup.group_multi_currency', self.group_multi_currency)