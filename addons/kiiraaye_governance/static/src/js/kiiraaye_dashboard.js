/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class KiiraayeDashboard extends Component {
    static template = "kiiraaye_governance.KiiraayeDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            view: "global",
            sectionTab: "synthese",
            data: null,
            filters: {
                section_id: false,
                organisation_id: false,
                geographie_id: false,
            },
            error: false,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call(
                "kiiraaye.dashboard",
                "get_dashboard_data",
                [{
                    ...this.state.filters,
                    view: this.state.view,
                }]
            );
        } catch (error) {
            this.state.error = error?.message || "Erreur de chargement";
        } finally {
            this.state.loading = false;
        }
    }

    async setView(view) {
        if (this.state.view === view) {
            return;
        }
        this.state.view = view;
        await this.loadDashboard();
    }

    async refresh() {
        await this.loadDashboard();
    }

    setSectionTab(tab) {
        this.state.sectionTab = tab;
    }

    get maxRegionMembers() {
        return Math.max(
            ...(this.state.data?.section_geography_overview || []).map((row) => row.members),
            1
        );
    }

    regionMemberShare(row) {
        const total = this.state.data?.kpis?.members || 0;
        return total ? (Number(row.members || 0) / total) * 100 : 0;
    }

    regionMemberLevel(row) {
        const share = this.regionMemberShare(row);
        if (share >= 15) {
            return "high";
        }
        if (share >= 5) {
            return "medium";
        }
        return "low";
    }

    async onFilterChange(field, ev) {
        const value = ev.target.value ? Number(ev.target.value) : false;
        this.state.filters[field] = value;
        await this.loadDashboard();
    }

    get maxSectionStatus() {
        return Math.max(
            ...(this.state.data?.section_statuses || []).map((row) => row.value),
            1
        );
    }

    get maxOrganisationStatus() {
        return Math.max(
            ...(this.state.data?.organisation_statuses || []).map((row) => row.value),
            1
        );
    }

    get maxGeographyValue() {
        return Math.max(
            ...(this.state.data?.geography_levels || []).map((row) => row.value),
            1
        );
    }

    get maxSectionMembers() {
        const rows = this.state.data?.sections || [];
        return Math.max(...rows.map((row) => row.members), 1);
    }

    get maxOrganisationMembers() {
        const rows = this.state.data?.organisations || [];
        return Math.max(...rows.map((row) => row.members), 1);
    }

    get maxCreationValue() {
        const rows = this.state.data?.member_creation || [];
        return Math.max(...rows.map((row) => row.value), 1);
    }

    get maxProjectionValue() {
        const rows = this.state.data?.member_projection || [];
        return Math.max(...rows.map((row) => row.value), 1);
    }

    barWidth(value, max) {
        return Math.max(4, Math.round((value / max) * 100));
    }

    formatNumber(value) {
        return new Intl.NumberFormat("fr-FR").format(value || 0);
    }

    formatPercent(value) {
        return new Intl.NumberFormat("fr-FR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(Number(value) || 0) + " %";
    }
}

registry.category("actions").add("kiiraaye_dashboard", KiiraayeDashboard);
