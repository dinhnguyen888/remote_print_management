# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.http import request, Request, db_filter
from odoo.addons.bus.websocket import wsrequest, WebsocketRequest


# -----------------------------------------------------------------------------
# 1. Hook database resolution for WebSocket (?db= parameter)
# -----------------------------------------------------------------------------
_orig_get_session_and_dbname = Request._get_session_and_dbname


def _remote_print_get_session_and_dbname(self):
    session, dbname = _orig_get_session_and_dbname(self)
    if not dbname and hasattr(self, 'httprequest'):
        host = self.httprequest.environ.get('HTTP_HOST', '')
        req_db = self.httprequest.args.get('db')
        if req_db and db_filter([req_db], host=host):
            session.db = dbname = req_db
    return session, dbname


if not getattr(Request, '_is_remote_print_db_patched', False):
    Request._get_session_and_dbname = _remote_print_get_session_and_dbname
    Request._is_remote_print_db_patched = True


# -----------------------------------------------------------------------------
# 2. Hook custom WebSocket event dispatcher
# -----------------------------------------------------------------------------
_orig_serve_ir_websocket = WebsocketRequest._serve_ir_websocket


def _remote_print_serve_ir_websocket(self, event_name, data):
    _orig_serve_ir_websocket(self, event_name, data)
    if event_name in ('agent_ping', 'agent_status', 'update_status'):
        try:
            self.env['ir.websocket']._serve_custom_websocket_event(event_name, data)
        except Exception:
            pass


if not getattr(WebsocketRequest, '_is_remote_print_patched', False):
    WebsocketRequest._serve_ir_websocket = _remote_print_serve_ir_websocket
    WebsocketRequest._is_remote_print_patched = True


# -----------------------------------------------------------------------------
# 3. IrWebsocket Model Extension
# -----------------------------------------------------------------------------
class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    @classmethod
    def _authenticate(cls):
        """Authenticate WebSocket connection via API Key (Bearer header or query param)."""
        req = request or wsrequest
        if req and hasattr(req, 'httprequest'):
            auth = req.httprequest.headers.get("Authorization", "")
            token = auth[7:].strip() if auth.lower().startswith("bearer ") else req.httprequest.args.get("api_key")
            if token:
                try:
                    uid = req.env['res.users.apikeys'].sudo()._check_credentials(scope='rpc', key=token)
                    if uid:
                        req.update_env(user=uid)
                        return
                except Exception:
                    pass
        super()._authenticate()

    def _build_bus_channel_list(self, channels):
        """Allow printer agent channels to subscribe."""
        res = super()._build_bus_channel_list(channels)
        for ch in channels:
            if isinstance(ch, str) and ch.startswith("printer_channel_client_") and ch not in res:
                res.append(ch)
        return res

    def _serve_custom_websocket_event(self, event_name, data):
        """Handle agent heartbeat, status/printers sync, and print job completion."""
        if not isinstance(data, dict):
            return

        client_id = data.get('client_id')
        now = fields.Datetime.now()

        if event_name in ('agent_ping', 'agent_status') and client_id:
            status = data.get('status', 'online') if event_name == 'agent_status' else 'online'
            node = self.env['printer.node'].sudo().search([
                '|', ('client_id', '=', str(client_id)), ('name', '=', str(client_id))
            ], limit=1)

            if not node and status == 'online':
                node = self.env['printer.node'].sudo().create({
                    'name': str(client_id),
                    'client_id': str(client_id),
                    'state': 'online',
                    'last_seen': now,
                })
            elif node:
                node.write({'state': status, 'last_seen': now})

            # Sync printer hardware details if provided in agent_status
            printers = data.get('printers')
            if isinstance(printers, dict):
                Printer = self.env['printer.details'].sudo()
                for p_key, p_data in printers.items():
                    printer = Printer.search([('client_id', '=', str(client_id)), ('id_of_printer', '=', p_key)], limit=1)
                    hw_st = p_data.get('status', 'online') if status == 'online' else 'device_offline'
                    p_vals = {'last_seen': now, 'hardware_status': hw_st, 'node_id': node.id if node else False}
                    if printer:
                        printer.write(p_vals)
                    elif status == 'online':
                        p_vals.update({
                            'client_id': str(client_id),
                            'id_of_printer': p_key,
                            'printers_name': p_data.get('printer_name', p_key),
                            'windows_printer_name': p_data.get('windows_printer_name', p_key),
                            'tray_options': p_data.get('trays', []),
                        })
                        Printer.create(p_vals)
            else:
                self.env['printer.details'].sudo().search([('client_id', '=', str(client_id))]).write({'last_seen': now})

        elif event_name == 'update_status':
            job_id, status = data.get('job_id'), data.get('status')
            if job_id and status:
                job = self.env['ir.attachment'].sudo().browse(int(job_id))
                if job.exists():
                    vals = {'print_status': status}
                    if data.get('error_message'):
                        vals['printer_error_message'] = str(data['error_message'])
                    job.write(vals)
                    if job.printer_id:
                        p_vals = {'last_seen': now}
                        if status == 'printed':
                            p_vals['hardware_status'] = 'online'
                        job.printer_id.write(p_vals)
