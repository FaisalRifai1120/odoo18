/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Layar progress untuk cetak NGP batch besar.
 * Me-render PDF per potongan lewat RPC berulang (render_next), lalu
 * menggabungkannya (finalize) dan mengunduh hasilnya.
 */
class KaCetakPrintProgress extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const params = (this.props.action && this.props.action.params) || {};
        this.jobId = params.job_id;

        this.state = useState({
            done: 0,
            total: params.total || 0,
            finished: false,
            merging: false,
            error: false,
        });

        onMounted(() => this._run());
    }

    get percent() {
        if (!this.state.total) {
            return 0;
        }
        return Math.round((this.state.done / this.state.total) * 100);
    }

    async _run() {
        try {
            let finished = false;
            while (!finished) {
                const res = await this.orm.call(
                    "ka.cetak.print.job",
                    "render_next",
                    [[this.jobId]]
                );
                this.state.done = res.done;
                this.state.total = res.total;
                finished = res.finished;
            }

            // Semua potongan selesai -> gabung jadi satu PDF
            this.state.merging = true;
            const fin = await this.orm.call(
                "ka.cetak.print.job",
                "finalize",
                [[this.jobId]]
            );
            this.state.merging = false;
            this.state.finished = true;

            // Picu unduhan file hasil
            this._download(fin.url);
        } catch (e) {
            this.state.error = true;
            throw e;
        }
    }

    _download(url) {
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "");
        document.body.appendChild(link);
        link.click();
        link.remove();
    }

    close() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

KaCetakPrintProgress.template = "ka_cetak.PrintProgress";
registry.category("actions").add("ka_cetak_print_progress", KaCetakPrintProgress);
