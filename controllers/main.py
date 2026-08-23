# -*- coding: utf-8 -*-
import io
import logging
from odoo import http, fields, _
from odoo.http import request, content_disposition

_logger = logging.getLogger(__name__)


class PrintAgentController(http.Controller):

    @http.route('/web/printing/export_excel', type='http', auth='user')
    def export_printer_excel(self, **kwargs):
        """
        Export printer status and failure report to Excel file.
        """
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response("xlsxwriter module is required", status=500)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Formats
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#1E3A8A'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#5B5FC7', 'font_color': '#FFFFFF', 'border': 1, 'align': 'center'})
        bold_fmt = workbook.add_format({'bold': True})
        cell_fmt = workbook.add_format({'border': 1})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center'})

        # Sheet 1: Overview
        sheet_summary = workbook.add_worksheet('Overview')
        sheet_summary.set_column('A:A', 30)
        sheet_summary.set_column('B:B', 25)

        sheet_summary.write('A1', 'Printer Status Summary Report', title_fmt)
        sheet_summary.write('A3', 'Exported At', bold_fmt)
        sheet_summary.write('B3', fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        printers = request.env['printer.details'].search([])
        online_printers = [p for p in printers if p.state == 'online']
        offline_printers = [p for p in printers if p.state == 'offline']
        failed_jobs = request.env['ir.attachment'].search([('print_status', '=', 'failed')])

        sheet_summary.write('A5', 'Total Printers Configured', bold_fmt)
        sheet_summary.write('B5', len(printers))
        sheet_summary.write('A6', 'Active / Online Printers', bold_fmt)
        sheet_summary.write('B6', len(online_printers))
        sheet_summary.write('A7', 'Inactive / Offline Printers', bold_fmt)
        sheet_summary.write('B7', len(offline_printers))
        sheet_summary.write('A8', 'Total Broken Printer / Failed Reports', bold_fmt)
        sheet_summary.write('B8', len(failed_jobs))

        # Sheet 2: Printers Detail
        sheet_printers = workbook.add_worksheet('Printers List')
        headers = ['Printer Name', 'Printer Code', 'Node', 'System Printer Name', 'Status', 'Last Seen']
        sheet_printers.set_column('A:F', 24)
        for col_idx, text in enumerate(headers):
            sheet_printers.write(0, col_idx, text, header_fmt)

        row = 1
        for p in printers:
            sheet_printers.write(row, 0, p.printers_name or '', cell_fmt)
            sheet_printers.write(row, 1, p.id_of_printer or '', cell_fmt)
            sheet_printers.write(row, 2, p.client_id or '', cell_fmt)
            sheet_printers.write(row, 3, p.windows_printer_name or '', cell_fmt)
            sheet_printers.write(row, 4, (p.state or 'unknown').capitalize(), center_fmt)
            sheet_printers.write(row, 5, fields.Datetime.context_timestamp(p, p.last_seen).strftime('%Y-%m-%d %H:%M:%S') if p.last_seen else '', center_fmt)
            row += 1

        # Sheet 3: Failed / Broken Job Reports
        sheet_failed = workbook.add_worksheet('Failed Job Reports')
        headers_failed = ['Job Name', 'Target Printer', 'Node', 'Sender', 'Date', 'Error Message']
        sheet_failed.set_column('A:F', 26)
        for col_idx, text in enumerate(headers_failed):
            sheet_failed.write(0, col_idx, text, header_fmt)

        row = 1
        for job in failed_jobs:
            sheet_failed.write(row, 0, job.name or '', cell_fmt)
            sheet_failed.write(row, 1, job.printer_id.printers_name if job.printer_id else '', cell_fmt)
            sheet_failed.write(row, 2, job.printer_id.client_id if job.printer_id else '', cell_fmt)
            sheet_failed.write(row, 3, job.create_uid.name if job.create_uid else '', cell_fmt)
            sheet_failed.write(row, 4, fields.Datetime.context_timestamp(job, job.create_date).strftime('%Y-%m-%d %H:%M:%S') if job.create_date else '', center_fmt)
            sheet_failed.write(row, 5, job.printer_error_message or '', cell_fmt)
            row += 1

        workbook.close()
        output.seek(0)

        filename = f"printer_status_report_{fields.Date.today().strftime('%Y%m%d')}.xlsx"
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )

    # -------------------------------------------------------------------------
    # Register Printers (HTTP JSON-RPC with native auth='bearer')
    # -------------------------------------------------------------------------
    @http.route('/web/printing/register_printers', type='json', auth='bearer', csrf=False, cors='*')
    def register_printers(self, client_id, printers, company_name=None, company_id=None, ip_address=None, os_info=None, agent_version=None, **kwargs):
        """
        Printer discovery registration endpoint triggered when agent starts.
        Resolves target company or defaults to the single system company; otherwise returns error.
        Uses native Odoo 18 Bearer authentication.
        """
        try:
            PrinterNode = request.env['printer.node'].sudo()
            PrinterDetails = request.env['printer.details'].sudo()
            ResCompany = request.env['res.company'].sudo()

            # ── 1. Resolve Target Company ────────────────────────────────────
            company = None
            if company_name:
                company = ResCompany.search([('name', '=ilike', str(company_name).strip())], limit=1)
                if not company:
                    return {'success': False, 'error': f"Company '{company_name}' not found on Odoo server."}
            elif company_id:
                try:
                    company = ResCompany.browse(int(company_id)).exists()
                except (ValueError, TypeError):
                    pass
                if not company:
                    return {'success': False, 'error': f"Company ID '{company_id}' not found on Odoo server."}
            else:
                all_companies = ResCompany.search([])
                if len(all_companies) == 1:
                    company = all_companies[0]
                else:
                    return {'success': False, 'error': "Multiple companies found on Odoo server. Please specify 'Company Name' in Printer Agent settings."}

            # ── 2. Create or Update Printer Node ─────────────────────────────
            node = PrinterNode.search([('client_id', '=', str(client_id))], limit=1)
            node_vals = {
                'company_id': company.id,
                'last_seen': fields.Datetime.now(),
            }
            if ip_address:
                node_vals['ip_address'] = ip_address
            if os_info:
                node_vals['os_info'] = os_info
            if agent_version:
                node_vals['agent_version'] = agent_version

            if node:
                node.write(node_vals)
            else:
                node_vals.update({
                    'name': str(client_id),
                    'client_id': str(client_id),
                })
                node = PrinterNode.create(node_vals)

            # ── 3. Create or Update Printer Details ──────────────────────────
            for p_key, p_data in printers.items():
                printer = PrinterDetails.search([
                    ('client_id', '=', str(client_id)),
                    ('id_of_printer', '=', p_key)
                ], limit=1)
                new_hw_status = p_data.get('status', 'online')
                if printer:
                    vals = {
                        'node_id': node.id,
                        'company_id': company.id,
                        'last_seen': fields.Datetime.now(),
                    }
                    if printer.hardware_status != new_hw_status:
                        vals.update({
                            'hardware_status': new_hw_status,
                            'tray_options': p_data.get('trays', []),
                            'printers_name': p_data.get('printer_name', p_key),
                            'windows_printer_name': p_data.get('windows_printer_name', p_key),
                        })
                    printer.write(vals)
                else:
                    PrinterDetails.create({
                        'node_id': node.id,
                        'client_id': str(client_id),
                        'company_id': company.id,
                        'id_of_printer': p_key,
                        'printers_name': p_data.get('printer_name', p_key),
                        'windows_printer_name': p_data.get('windows_printer_name', p_key),
                        'tray_options': p_data.get('trays', []),
                        'hardware_status': new_hw_status,
                        'last_seen': fields.Datetime.now(),
                    })
            return {'success': True}
        except Exception as e:
            _logger.error("Register printers error: %s", e)
            return {'success': False, 'error': str(e)}