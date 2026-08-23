# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class PrinterDetails(models.Model):
    _name = "printer.details"
    _description = "Printer Details"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "printers_name"

    id_of_printer = fields.Char(
        string="Printer Key",
        required=True,
        tracking=True,
        readonly=True,
        help="Stable unique key used by Odoo and the printer agent.",
    )
    printers_name = fields.Char(
        string="Printer Name",
        required=True,
        tracking=True,
        readonly=True,
        help="Display name shown in Odoo.",
    )
    printer_description = fields.Char(string="Printer Description", tracking=True)
    node_id = fields.Many2one(
        "printer.node",
        string="Printer Node",
        ondelete="cascade",
        index=True,
        help="Agent Node running this printer.",
    )
    client_id = fields.Char(
        string="Node Key",
        required=True,
        readonly=True,
        tracking=True,
        help="Node instance that processes jobs for this printer.",
    )
    windows_printer_name = fields.Char(
        string="System Printer Name",
        required=True,
        readonly=True,
        tracking=True,
        help="Exact printer name on the client operating system.",
    )
    hardware_status = fields.Selection(
        [
            ("online", "Ready"),
            ("device_offline", "Printer Off / Disconnected"),
            ("paper_out", "Paper Out"),
            ("paper_jam", "Paper Jam"),
            ("door_open", "Door Open"),
            ("error", "Hardware Error"),
            ("unknown", "Unknown"),
        ],
        string="Hardware Status",
        default="online",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("online", "Online (Ready)"),
            ("device_offline", "Printer Off / Disconnected"),
            ("paper_out", "Paper Out"),
            ("paper_jam", "Paper Jam"),
            ("door_open", "Door Open"),
            ("error", "Hardware Error"),
            ("offline", "Offline (Agent Down)"),
            ("unknown", "Unknown"),
        ],
        string="Status",
        compute="_compute_state",
        search="_search_state",
        default="unknown",
        readonly=True,
        tracking=True,
    )
    last_seen = fields.Datetime(
        string="Last Seen",
        index=True,
        readonly=True,
    )
    tray_options = fields.Json(
        string="Paper Trays",
        help="Paper trays published by the local printer agent.",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
        help="Company owning or allowed to use this printer.",
    )

    @api.depends("node_id.state", "hardware_status")
    def _compute_state(self):
        for record in self:
            if not record.node_id or record.node_id.state == "offline":
                record.state = "offline"
            else:
                record.state = record.hardware_status or "online"

    def _search_state(self, operator, value):
        if value == "offline":
            return ["|", ("node_id", "=", False), ("node_id.state", "=", "offline")]
        elif value == "online":
            return [("node_id.state", "=", "online"), ("hardware_status", "=", "online")]
        elif value == "device_offline":
            return [("node_id.state", "=", "online"), ("hardware_status", "=", "device_offline")]
        elif value in ("paper_out", "paper_jam", "door_open", "error"):
            return [("node_id.state", "=", "online"), ("hardware_status", "=", value)]
        return []

    def action_revoke(self):
        """
        Delete printer record.
        """
        return self.unlink()


class QuickPrintWizard(models.TransientModel):
    _name = "quick.print.wizard"
    _description = "Quick Print Wizard"

    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    document = fields.Binary(string="Document")
    file_name = fields.Char(string="File Name")
    printer_id = fields.Many2one('printer.details', string="Printer", required=True)

    def action_print(self):
        for record in self:
            if not record.printer_id:
                raise UserError(_("Please select a printer."))

            attachment = record.attachment_id
            if not attachment and record.document:
                attachment = self.env['ir.attachment'].create({
                    'name': record.file_name or 'Quick_Print_Document',
                    'type': 'binary',
                    'datas': record.document,
                    'print_status': 'pending',
                    'printer_id': record.printer_id.id,
                })
            elif attachment:
                attachment.write({
                    'name': record.file_name or attachment.name or 'Quick_Print_Document',
                    'printer_id': record.printer_id.id,
                    'print_status': 'pending',
                })
            else:
                raise UserError(_("Please upload a document to print."))

        return {'type': 'ir.actions.act_window_close'}
