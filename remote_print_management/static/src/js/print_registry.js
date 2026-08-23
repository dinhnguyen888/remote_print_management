/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { OpenDirectPrinterDialog } from "./open_direct_printer";

registry
    .category("ir.actions.report handlers")
    .add("remote_print_pdf_options", async (action, options, env) => {
        const { default_print_option: printOption, report_type } = action;
        if (report_type !== "qweb-pdf" || printOption === "download") {
            return false;
        }

        // 1. Silent Print or Modal Data check
        try {
            const modalData = await rpc("/web/dataset/call_kw/ir.actions.report/get_modal_data_from_report_action", {
                model: "ir.actions.report",
                method: "get_modal_data_from_report_action",
                args: [action],
                kwargs: {},
            });

            if (modalData && modalData.enable_silent_print && modalData.default_printer_ids && modalData.default_printer_ids.length > 0) {
                env.services.ui.block();
                try {
                    await rpc("/web/dataset/call_kw/ir.actions.report/create_from_report_action", {
                        model: "ir.actions.report",
                        method: "create_from_report_action",
                        args: [action.id || false, action, modalData.default_printer_ids],
                        kwargs: { copies: 1, tray_id: "default" },
                    });
                    env.services.notification.add(_t("Remote print job created silently."), {
                        type: "success",
                    });
                } catch (err) {
                    env.services.notification.add(err.message || _t("Failed to send remote print job."), {
                        type: "danger",
                    });
                } finally {
                    env.services.ui.unblock();
                }
                return true;
            }
        } catch (e) {
            console.error("Error checking silent print data", e);
        }

        // 2. Open Direct Printer OWL Dialog
        const components = registry.category("remote_print_management.direct_print_components");
        const DirectPrinterDialog = components.get("open_direct_printer") || OpenDirectPrinterDialog;
        let removeDialog;
        await new Promise((resolve) => {
            removeDialog = env.services.dialog.add(
                DirectPrinterDialog,
                { action, onDone: resolve },
                { onClose: resolve }
            );
        });
        removeDialog();
        return true;
    });
