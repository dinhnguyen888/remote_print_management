# -*- coding: utf-8 -*-
from odoo import fields, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    # Submenu Visibility Permissions
    printer_menu_dashboard = fields.Boolean(
        string="Dashboard Menu",
        default=True,
        help="Allow members of this group to view the Dashboard menu."
    )
    printer_menu_printers = fields.Boolean(
        string="Direct Printers Menu",
        default=True,
        help="Allow members of this group to view the Direct Printers menu."
    )
    printer_menu_jobs = fields.Boolean(
        string="Direct Print Jobs Menu",
        default=True,
        help="Allow members of this group to view the Direct Print Jobs menu."
    )
    printer_menu_tokens = fields.Boolean(
        string="Agent Tokens Menu",
        default=True,
        help="Allow members of this group to view the Agent Tokens menu."
    )
    printer_menu_config = fields.Boolean(
        string="Configuration Menu",
        default=True,
        help="Allow members of this group to view the Configuration menu."
    )

    # Dashboard Component Permissions
    printer_show_kpis = fields.Boolean(
        string="Show Dashboard KPIs",
        default=True,
        help="Allow members of this group to view KPI summary cards on the Dashboard."
    )
    printer_show_chart = fields.Boolean(
        string="Show Hourly Volume Chart",
        default=True,
        help="Allow members of this group to view the Hourly Print Volume chart."
    )
    printer_show_lanes = fields.Boolean(
        string="Show Job Swimlanes",
        default=True,
        help="Allow members of this group to view Pending, Printing, and Failed job lanes."
    )
    printer_show_agents = fields.Boolean(
        string="Show Agents & Printers Section",
        default=True,
        help="Allow members of this group to view the Agents & Printers list."
    )
    printer_show_recent_jobs = fields.Boolean(
        string="Show Recent Jobs Section",
        default=True,
        help="Allow members of this group to view the Recent Jobs table."
    )
    printer_allow_quick_print = fields.Boolean(
        string="Allow Quick Print Action",
        default=True,
        help="Allow members of this group to trigger Quick Print wizard."
    )
    printer_allow_export_report = fields.Boolean(
        string="Allow Export Report Action",
        default=True,
        help="Allow members of this group to download Excel status report."
    )
