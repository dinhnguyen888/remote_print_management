# -*- coding: utf-8 -*-
from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _filter_visible_menus(self):
        res = super()._filter_visible_menus()
        user_groups = self.env.user.groups_id
        if not user_groups:
            return res

        menu_permissions_map = {
            'remote_print_management.direct_printer_root_menu': 'printer_menu_dashboard',
            'remote_print_management.printer_details_menu': 'printer_menu_printers',
            'remote_print_management.direct_printer_job_menu': 'printer_menu_jobs',
            'remote_print_management.printer_agent_token_menu': 'printer_menu_tokens',
            'remote_print_management.menu_direct_print_config': 'printer_menu_config',
        }

        menus_to_hide = set()
        for xml_id, group_field in menu_permissions_map.items():
            if not any(getattr(g, group_field, False) for g in user_groups):
                menu = self.env.ref(xml_id, raise_if_not_found=False)
                if menu:
                    menus_to_hide.add(menu.id)

        if not menus_to_hide:
            return res

        return res.filtered(lambda m: m.id not in menus_to_hide)
