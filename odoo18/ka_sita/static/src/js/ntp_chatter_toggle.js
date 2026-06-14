/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/*
 * Widget tombol show/hide chatter pada form NTP.
 * Chatter di posisi default Odoo 18 (samping kanan).
 * Default tampil, bisa disembunyikan agar data lebih leluasa.
 */
export class NtpChatterToggle extends Component {
    static template = "ka_sita.NtpChatterToggle";
    static props = { ...standardWidgetProps };

    toggleChatter() {
        const form = document.querySelector(".o_ka_ntp_form");
        if (form) {
            form.classList.toggle("o_ntp_chatter_hidden");
        }
    }
}

export const ntpChatterToggle = {
    component: NtpChatterToggle,
};
registry.category("view_widgets").add("ntp_chatter_toggle", ntpChatterToggle);
