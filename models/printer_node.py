# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta
from odoo.addons.bus.models.bus import dispatch


class PrinterNode(models.Model):
    _name = "printer.node"
    _description = "Printer Agent Node"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id desc"

    name = fields.Char(
        string="Node Name",
        required=True,
        tracking=True,
        help="Display name for this agent node (e.g. Warehouse Packing Station 1)."
    )
    client_id = fields.Char(
        string="Node Key (Client ID)",
        required=True,
        index=True,
        tracking=True,
        help="Unique Identifier sent by the local Printer Agent."
    )
    ip_address = fields.Char(string="IP Address", tracking=True)
    os_info = fields.Char(string="OS / Platform", tracking=True)
    agent_version = fields.Char(string="Agent Version", tracking=True)
    last_seen = fields.Datetime(string="Last Seen", index=True, readonly=True)
    
    state = fields.Selection([
        ('online', 'Online (Connected)'),
        ('offline', 'Offline (Agent Down)'),
        ('unknown', 'Unknown'),
    ], string="Status", compute="_compute_state", search="_search_state", default="offline", tracking=True)

    printer_ids = fields.One2many("printer.details", "node_id", string="Connected Printers")
    printer_count = fields.Integer(string="Printers Count", compute="_compute_printer_count")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company, index=True)
    notes = fields.Text(string="Notes")

    _sql_constraints = [
        ('client_id_uniq', 'unique(client_id)', 'The Client ID (Node Key) must be unique!'),
    ]

    def _compute_state(self):
        db_name = self.env.cr.dbname
        for node in self:
            if not node.client_id:
                node.state = "offline"
                continue
            channel_key = (db_name, f"printer_channel_client_{node.client_id}")
            active_sockets = dispatch._channels_to_ws.get(channel_key)
            if active_sockets and len(active_sockets) > 0:
                node.state = "online"
            else:
                node.state = "offline"

    def _search_state(self, operator, value):
        db_name = self.env.cr.dbname
        online_client_ids = []
        for (db, ch), sockets in dispatch._channels_to_ws.items():
            if db == db_name and isinstance(ch, str) and ch.startswith("printer_channel_client_") and sockets:
                online_client_ids.append(ch.replace("printer_channel_client_", ""))

        if value == "online":
            return [("client_id", "in", online_client_ids)]
        elif value == "offline":
            return [("client_id", "not in", online_client_ids)]
        return []

    @api.depends("printer_ids")
    def _compute_printer_count(self):
        for node in self:
            node.printer_count = len(node.printer_ids)
