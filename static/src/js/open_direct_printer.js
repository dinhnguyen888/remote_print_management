/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class OpenDirectPrinterDialog extends Dialog {
    static template = "remote_print_management.OpenDirectPrinterDialog";
    static props = {
        ...Dialog.props,
        slots: { type: Object, optional: true },
        action: Object,
        onDone: Function,
        close: { type: Function, optional: true },
    };
    static defaultProps = {
        ...Dialog.defaultProps,
        size: "xl",
        title: _t("Remote Print"),
        withBodyPadding: true,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            printing: false,
            nodes: [],
            previewUrl: "",
            nodeId: "",
            printerId: "",
            trayId: "default",
            copies: 1,
            multiplePrinters: false,
            selectedPrinterIds: [],
        });

        onWillStart(async () => {
            const data = await this.orm.call(
                "ir.actions.report",
                "get_modal_data_from_report_action",
                [this.props.action]
            );
            this.state.nodes = data.nodes || [];
            let previewUrl = data.preview_url || "";
            if (previewUrl && !previewUrl.includes("#")) {
                previewUrl += "#toolbar=0&navpanes=0";
            }
            this.state.previewUrl = previewUrl;
            this.state.loading = false;

            const firstNode = this.state.nodes[0];
            if (firstNode) {
                this.state.nodeId = firstNode.id;
                this.selectPrinter(firstNode.printers[0]);
            }
        });
    }

    get selectedNode() {
        return this.state.nodes.find((node) => node.id === this.state.nodeId);
    }

    get availablePrinters() {
        return this.selectedNode ? this.selectedNode.printers : [];
    }

    get selectedPrinter() {
        const printerId = Number(this.state.printerId);
        return this.availablePrinters.find((printer) => printer.id === printerId);
    }

    get availableTrays() {
        return this.selectedPrinter ? this.selectedPrinter.trays : [];
    }

    get usesDefaultTrays() {
        return this.availableTrays.length === 1 && this.availableTrays[0].id === "default";
    }

    onNodeChange(ev) {
        this.state.nodeId = ev.target.value;
        this.selectPrinter(this.availablePrinters[0]);
        this.state.trayId = "default";
    }

    onPrinterChange(ev) {
        const printerId = Number(ev.target.value);
        this.selectPrinter(this.availablePrinters.find((printer) => printer.id === printerId));
        this.state.trayId = "default";
    }

    onTrayChange(ev) {
        this.state.trayId = ev.target.value;
    }

    onCopiesChange(ev) {
        this.state.copies = Math.max(Number(ev.target.value || 1), 1);
    }

    onMultiplePrintersChange(ev) {
        this.state.multiplePrinters = ev.target.checked;
        if (!this.state.multiplePrinters && this.state.printerId) {
            this.state.selectedPrinterIds = [Number(this.state.printerId)];
        }
    }

    isPrinterChecked(printerId) {
        return this.state.selectedPrinterIds.includes(printerId);
    }

    togglePrinter(ev) {
        const printerId = Number(ev.target.value);
        if (ev.target.checked) {
            this.state.selectedPrinterIds = [...new Set([...this.state.selectedPrinterIds, printerId])];
            return;
        }
        this.state.selectedPrinterIds = this.state.selectedPrinterIds.filter((id) => id !== printerId);
    }

    selectPrinter(printer) {
        this.state.printerId = printer ? String(printer.id) : "";
        this.state.selectedPrinterIds = printer ? [printer.id] : [];
    }

    async printDirect() {
        const printerIds = this.state.multiplePrinters
            ? this.state.selectedPrinterIds
            : [Number(this.state.printerId)].filter(Boolean);

        if (!printerIds.length) {
            this.env.services.notification.add(_t("Please select at least one printer."), {
                type: "warning",
            });
            return;
        }

        this.state.printing = true;
        try {
            await this.orm.call(
                "ir.actions.report",
                "create_from_report_action",
                [this.props.action.id, this.props.action, printerIds],
                {
                    copies: this.state.copies,
                    tray_id: this.state.trayId,
                }
            );
            this.env.services.notification.add(_t("Remote print job was created."), {
                type: "success",
            });
            this.closeDialog();
        } finally {
            this.state.printing = false;
        }
    }

    cancel() {
        this.closeDialog();
    }

    closeDialog() {
        this.props.onDone();
        if (this.props.close) {
            this.props.close();
        }
    }
}

registry
    .category("remote_print_management.direct_print_components")
    .add("open_direct_printer", OpenDirectPrinterDialog);
