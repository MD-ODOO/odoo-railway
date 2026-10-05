/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ImobilierSNDashboard extends Component {
    static template = "imobilier_sn.Dashboard";
    static props = {
        action: { type: Object, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            error: false,
            options: { locations: [], years: [], default_year: new Date().getFullYear() },
            filters: { year: new Date().getFullYear(), location: "" },
            data: null,
        });

        onWillStart(async () => {
            try {
                this.state.options = await this.orm.call(
                    "imobilier.sn.dashboard",
                    "get_filter_options",
                    [],
                );
                this.state.filters.year = this.state.options.default_year;
                await this.loadData();
            } catch (error) {
                this.state.error = error.message || String(error);
                this.state.loading = false;
            }
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = false;
        try {
            await this.orm.call(
                "imobilier.sn.dashboard",
                "action_generate_current_month_rents",
                [],
            );
            this.state.data = await this.orm.call(
                "imobilier.sn.dashboard",
                "get_dashboard_data",
                [this.state.filters.year, this.state.filters.location],
            );
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    onYearChange(ev) {
        this.state.filters.year = parseInt(ev.target.value, 10);
        this.loadData();
    }

    onLocationChange(ev) {
        this.state.filters.location = ev.target.value;
        this.loadData();
    }

    refresh() {
        return this.loadData();
    }

    fmtInt(value) {
        return Number(value || 0).toLocaleString("fr-FR");
    }

    fmtMoney(value) {
        const symbol = (this.state.data && this.state.data.currency_symbol) || "FCFA";
        return Number(value || 0).toLocaleString("fr-FR") + " " + symbol;
    }

    collectionWidth() {
        const rate = Number(this.state.data && this.state.data.kpi.rent_collection_rate || 0);
        return Math.max(0, Math.min(100, rate));
    }

    badgeClass(status) {
        return status === "paid" ? "o_immo_badge_paid" : "o_immo_badge_due";
    }

    openPayments(paid) {
        return this.orm.call(
            "imobilier.sn.contract.payment",
            "action_current_month_payments",
            [paid, this.state.filters.location],
        ).then((action) => this.action.doAction(action));
    }

    openProperties(type = false) {
        const domain = [];
        if (type) {
            domain.push(["property_type", "=", type]);
        }
        if (this.state.filters.location) {
            domain.push(["location", "=", this.state.filters.location]);
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Biens immobiliers",
            res_model: "imobilier.sn.property",
            view_mode: "list,form",
            domain,
        });
    }
}

registry.category("actions").add("imobilier_sn.dashboard", ImobilierSNDashboard);
