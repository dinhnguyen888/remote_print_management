# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    print_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('printing', 'Printing'),
        ('printed', 'Printed'),
        ('failed', 'Failed')
    ], string='Print Status', default='draft', index=True)

    printer_id = fields.Many2one('printer.details', string='Printer', index=True)
    printer_error_message = fields.Text('Printer Error Message')
    copies = fields.Integer(string='Copies', default=1)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.print_status in ('pending', 'draft') and record.printer_id:
                record._notify_printer_agent()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'print_status' in vals and vals['print_status'] in ('pending', 'draft'):
            for record in self:
                if record.printer_id:
                    record._notify_printer_agent()
        return res

    def _notify_printer_agent(self):
        self.ensure_one()
        client_id = self.printer_id.client_id
        if not client_id:
            return
        channel_name = f"printer_channel_client_{client_id}"
        file_data = False
        if self.datas:
            file_data = self.datas.decode('utf-8') if isinstance(self.datas, bytes) else self.datas

        payload = {
            "action": "print_job",
            "job_id": self.id,
            "name": self.name or "document",
            "report_name": self.name or "document",
            "copies": getattr(self, 'copies', 1) or 1,
            "tray_id": "default",
            "file_data": file_data,
            "windows_printer_name": self.printer_id.windows_printer_name or self.printer_id.printers_name,
            "printer_name": self.printer_id.printers_name,
        }
        self.env['bus.bus']._sendone(channel_name, 'print_job', payload)

    @api.model
    def get_direct_printer_dashboard_data(self, params):
        printers = self.env['printer.details'].search([])

        status_labels = {
            'online': 'Online (Ready)',
            'device_offline': 'Printer Off',
            'paper_out': 'Paper Out',
            'paper_jam': 'Paper Jam',
            'door_open': 'Door Open',
            'error': 'Error',
            'offline': 'Offline (Agent Down)',
            'unknown': 'Unknown',
        }
        agents_data = []
        clients_set = set()
        for printer in printers:
            clients_set.add(printer.client_id or 'unknown')
            st = printer.state or 'unknown'
            agents_data.append({
                'id': printer.id,
                'name': printer.printers_name,
                'client_id': printer.client_id,
                'status': st,
                'detail': f"{printer.windows_printer_name} (Node: {printer.client_id})",
                'label': status_labels.get(st, st.capitalize())
            })

        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        # Calculate KPI 1 & 2 (Pages & Time)
        printed_today = self.search([('print_status', '=', 'printed'), ('printer_id', '!=', False), ('write_date', '>=', today_start)])
        printed_yesterday = self.search([('print_status', '=', 'printed'), ('printer_id', '!=', False), ('write_date', '>=', yesterday_start), ('write_date', '<', today_start)])

        total_pages_today = sum(getattr(job, 'copies', 1) or 1 for job in printed_today)
        total_pages_yesterday = sum(getattr(job, 'copies', 1) or 1 for job in printed_yesterday)

        if total_pages_yesterday > 0:
            page_diff_percent = round(((total_pages_today - total_pages_yesterday) / total_pages_yesterday) * 100)
        else:
            page_diff_percent = 100 if total_pages_today > 0 else 0

        print_times = []
        for job in printed_today:
            if job.write_date and job.create_date:
                print_times.append((job.write_date - job.create_date).total_seconds())

        avg_time = round(sum(print_times) / len(print_times), 1) if print_times else 0.0
        max_time = round(max(print_times), 1) if print_times else 0.0

        online_printers = len([p for p in printers if p.state == 'online'])
        active_clients_count = len(set(p.client_id for p in printers if p.state != 'offline' and p.client_id))

        pending_count = self.search_count([('print_status', 'in', ['pending', 'draft']), ('printer_id', '!=', False)])
        printing_count = self.search_count([('print_status', '=', 'printing'), ('printer_id', '!=', False)])
        done_today_count = len(printed_today)
        failed_count = self.search_count([('print_status', '=', 'failed'), ('printer_id', '!=', False)])

        kpis = {
            'total_pages_today': total_pages_today,
            'page_diff_percent': page_diff_percent,
            'jobs_today_count': done_today_count,
            'avg_time': avg_time,
            'max_time': max_time,
            'online_printers': online_printers,
            'total_printers': len(printers),
            'active_clients': active_clients_count,
            'failed': failed_count,
            'done_today': done_today_count,
            'pending': pending_count,
            'printing': printing_count,
        }

        pending_jobs = self.search([('print_status', 'in', ['pending', 'draft']), ('printer_id', '!=', False)], order='create_date desc', limit=50)
        printing_jobs = self.search([('print_status', '=', 'printing'), ('printer_id', '!=', False)], order='create_date desc', limit=50)
        failed_jobs = self.search([('print_status', '=', 'failed'), ('printer_id', '!=', False)], order='create_date desc', limit=50)

        def map_job(j):
            return {
                'id': j.id,
                'name': j.name,
                'printer': j.printer_id.printers_name or 'Unknown',
                'copies': getattr(j, 'copies', 1)
            }

        lanes = {
            'pending': [map_job(j) for j in pending_jobs],
            'printing': [map_job(j) for j in printing_jobs],
            'failed': [map_job(j) for j in failed_jobs]
        }

        recent_jobs = self.search([('printer_id', '!=', False)], order='create_date desc', limit=50)
        jobs_data = []
        for rj in recent_jobs:
            jobs_data.append({
                'id': rj.id,
                'time': fields.Datetime.context_timestamp(rj, rj.create_date).strftime('%Y-%m-%d %H:%M:%S') if rj.create_date else '',
                'name': rj.name,
                'printer': rj.printer_id.printers_name or 'Unknown',
                'client': rj.printer_id.client_id or 'Unknown',
                'sender': rj.create_uid.name or 'System',
                'copies': getattr(rj, 'copies', 1),
                'state': rj.print_status
            })

        chart_data = []
        for i in range(5, -1, -1):
            h_time = fields.Datetime.now() - timedelta(hours=i)
            h_start = h_time.replace(minute=0, second=0, microsecond=0)
            h_end = h_start + timedelta(hours=1)

            done_h = self.search_count([('print_status', '=', 'printed'), ('printer_id', '!=', False), ('write_date', '>=', h_start), ('write_date', '<', h_end)])
            print_h = self.search_count([('print_status', '=', 'printing'), ('printer_id', '!=', False), ('write_date', '>=', h_start), ('write_date', '<', h_end)])
            fail_h = self.search_count([('print_status', '=', 'failed'), ('printer_id', '!=', False), ('write_date', '>=', h_start), ('write_date', '<', h_end)])

            label = fields.Datetime.context_timestamp(self, h_time).strftime('%H:00')
            chart_data.append({
                'label': label,
                'done': done_h,
                'printing': print_h,
                'failed': fail_h
            })

        user_groups = self.env.user.groups_id
        if user_groups:
            permissions = {
                'show_kpis': any(g.printer_show_kpis for g in user_groups),
                'show_chart': any(g.printer_show_chart for g in user_groups),
                'show_lanes': any(g.printer_show_lanes for g in user_groups),
                'show_agents': any(g.printer_show_agents for g in user_groups),
                'show_recent_jobs': any(g.printer_show_recent_jobs for g in user_groups),
                'allow_quick_print': any(g.printer_allow_quick_print for g in user_groups),
                'allow_export_report': any(g.printer_allow_export_report for g in user_groups),
            }
        else:
            permissions = {
                'show_kpis': True,
                'show_chart': True,
                'show_lanes': True,
                'show_agents': True,
                'show_recent_jobs': True,
                'allow_quick_print': True,
                'allow_export_report': True,
            }

        return {
            'kpis': kpis,
            'chart': chart_data,
            'lanes': lanes,
            'agents': agents_data,
            'jobs': jobs_data,
            'clients': list(clients_set),
            'permissions': permissions,
        }
