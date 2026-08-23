# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    default_print_option = fields.Selection(
        selection=[
            ("print", "Print"),
            ("download", "Download"),
            ("open", "Open"),
            ("direct_print", "Direct Print"),
        ],
        string="Default printing option",
    )

    def _get_readable_fields(self):
        readable_fields = super()._get_readable_fields()
        readable_fields.add("default_print_option")
        return readable_fields

    def report_action(self, docids, data=None, config=True):
        action = super().report_action(docids, data=data, config=config)
        action["id"] = self.id
        action["default_print_option"] = self.default_print_option
        return action

    @api.model
    def get_modal_data_from_report_action(self, action):
        company = self.env.company
        company_id = company.id
        printers = self.env['printer.details'].search([
            '|', ('company_id', '=', False), ('company_id', '=', company_id)
        ])

        nodes_by_client = {}
        for p in printers:
            c_id = p.client_id or 'default'
            if c_id not in nodes_by_client:
                nodes_by_client[c_id] = {
                    'id': c_id,
                    'name': f"Node ({c_id})",
                    'printers': []
                }
            trays = p.tray_options if isinstance(p.tray_options, list) else [{'id': 'default', 'name': 'Default Tray'}]
            nodes_by_client[c_id]['printers'].append({
                'id': p.id,
                'name': p.printers_name or p.id_of_printer,
                'client_id': p.client_id or '',
                'trays': trays
            })

        nodes = list(nodes_by_client.values())
        if not nodes:
            nodes = [{
                'id': 'all',
                'name': 'All Printers',
                'printers': []
            }]

        active_ids = action.get("context", {}).get("active_ids", [])
        docids_str = ",".join(map(str, active_ids)) if active_ids else ""
        report_name = action.get("report_name", "")
        preview_url = f"/report/pdf/{report_name}/{docids_str}#toolbar=0&navpanes=0" if docids_str else f"/report/pdf/{report_name}#toolbar=0&navpanes=0"

        enable_silent_print = company.enable_silent_print
        default_printer_ids = []
        if company.multiple_printers and company.printers_ids:
            default_printer_ids = company.printers_ids.ids
        elif company.available_printers_id:
            default_printer_ids = [company.available_printers_id.id]
        elif printers:
            default_printer_ids = [printers[0].id]

        return {
            'nodes': nodes,
            'preview_url': preview_url,
            'enable_silent_print': enable_silent_print,
            'default_printer_ids': default_printer_ids,
        }

    def create_from_report_action(self, action, printer_ids, copies=1, tray_id='default'):
        if not printer_ids:
            raise UserError(_("No printer selected."))

        res_ids = action.get('context', {}).get('active_ids', [])
        report_record = self if (self and len(self) == 1) else self.env['ir.actions.report'].search([('id', '=', action.get('id'))], limit=1)
        if not report_record and action.get('report_name'):
            report_record = action.get('report_name')

        pdf_content, _ = self._render_qweb_pdf(report_record, res_ids=res_ids)

        for printer_id in printer_ids:
            printer = self.env['printer.details'].browse(printer_id)
            if not printer.exists():
                continue

            # Create attachment record in Odoo (triggers WebSocket dispatch to agent)
            self.env['ir.attachment'].create({
                'name': f"{action.get('name', 'Report')}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self.model,
                'res_id': res_ids[0] if res_ids else 0,
                'print_status': 'pending',
                'printer_id': printer.id,
                'copies': copies,
            })

        return True
