# -*- coding: utf-8 -*-
from odoo import models, fields, _


class PrinterAgentApiKeyWizard(models.TransientModel):
    _name = 'printer.agent.apikey.wizard'
    _inherit = 'res.users.apikeys.description'
    _description = 'Generate Printer Agent API Key'

    name = fields.Char(
        string="Key Description / Label",
        default="Printer Agent Key",
        help="Label to identify this API key (e.g. Warehouse Laptop, Office Print Server)"
    )

    def action_generate_key(self):
        self.ensure_one()
        self.env['res.users.apikeys']._check_expiration_date(self.expiration_date)

        # Find printer_agent user, fallback to current user
        agent_user = self.env['res.users'].search([('login', '=', 'printer_agent')], limit=1)
        target_user = agent_user or self.env.user

        key_name = self.name or "Printer Agent Key"
        if "Printer Agent" not in key_name:
            key_name = f"Printer Agent - {key_name}"

        # Generate persistent or expirable key for target user
        key_secret = self.env['res.users.apikeys'].with_user(target_user).sudo()._generate(
            scope=None,
            name=key_name,
            expiration_date=self.expiration_date or None,
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.apikeys.show',
            'name': _('Printer Agent API Key Created'),
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_key': key_secret,
            }
        }
