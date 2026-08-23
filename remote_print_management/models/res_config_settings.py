# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    """Remote printer settings exposed in Odoo general settings."""
    _inherit = "res.config.settings"

    available_printers_id = fields.Many2one(
        "printer.details",
        related="company_id.available_printers_id",
        readonly=False,
    )
    printers_ids = fields.Many2many(
        "printer.details",
        related="company_id.printers_ids",
        readonly=False,
    )
    multiple_printers = fields.Boolean(
        related="company_id.multiple_printers",
        readonly=False,
    )
    enable_silent_print = fields.Boolean(
        related="company_id.enable_silent_print",
        readonly=False,
        string="Enable Silent Printer Toggle",
        help="Automatically select default printer without opening prompt modal.",
    )
    def action_download_agent(self):
        """Open download link for Printer Agent packages in a new browser tab."""
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://drive.google.com/drive/u/0/folders/1UZofsBf5Wu1v_6uoqMHQEsmTUtBsBhst',
            'target': 'new',
        }


    def action_scan_printers(self):
        self.ensure_one()
        printers = self.env['printer.details'].search([
            ('client_id', '!=', False),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)
        ])

        # Collect unique clients to broadcast scan request
        notified_clients = set()
        for printer in printers:
            client_id = printer.client_id
            if client_id not in notified_clients:
                channel = f"printer_channel_client_{client_id}"
                self.env['bus.bus']._sendone(channel, 'scan_printers', 'scan_printers')
                notified_clients.add(client_id)

        # Broadcast to company channel
        generic_channel = f"printer_channel_company_{self.company_id.id}_broadcast"
        self.env['bus.bus']._sendone(generic_channel, 'scan_printers', 'scan_printers')

        return self._notification(_("Scan request sent to all local agents. Please check dashboard in a few seconds."), "success")

    def _notification(self, message, notification_type="info"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Remote Print"),
                "message": message,
                "type": notification_type,
                "sticky": False,
            },
        }
