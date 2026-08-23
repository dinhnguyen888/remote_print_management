# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """Remote printer settings per company."""
    _inherit = "res.company"

    available_printers_id = fields.Many2one(
        "printer.details",
        string="Default Printer",
        help="Default printer used for report printing.",
    )
    printers_ids = fields.Many2many(
        "printer.details",
        string="Allowed Printers",
        help="Printers allowed for this company.",
    )
    multiple_printers = fields.Boolean(
        string="Multiple Printers",
        help="Send each report to all selected printers.",
    )
    enable_silent_print = fields.Boolean(
        string="Enable Silent Printer Toggle",
        default=True,
        help="Automatically select default/mapped printer without showing confirmation modal.",
    )
