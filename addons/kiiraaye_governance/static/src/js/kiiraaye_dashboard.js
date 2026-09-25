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
            view: "section",
            sectionScope: "national",
            selectedRegionId: false,
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
                    section_scope: this.state.sectionScope,
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

    async setSectionScope(scope) {
        if (this.state.sectionScope === scope) {
            return;
        }
        this.state.sectionScope = scope;
        // Les filtres géographiques sénégalais ne doivent pas polluer la vue diaspora.
        if (scope === "diaspora") {
            this.state.filters.geographie_id = false;
        }
        this.state.filters.section_id = false;
        await this.loadDashboard();
    }

    coveragePercent(occupied, total) {
        const denominator = Number(total) || 0;
        return denominator ? (Number(occupied || 0) / denominator) * 100 : 0;
    }

    coverageClass(occupied, total) {
        const ratio = this.coveragePercent(occupied, total);
        if (!Number(total)) {
            return "empty";
        }
        if (ratio >= 100) {
            return "complete";
        }
        if (ratio >= 66) {
            return "high";
        }
        if (ratio >= 33) {
            return "medium";
        }
        return "low";
    }

    coverageLabel(occupied, total) {
        return this.formatNumber(occupied) + " / " + this.formatNumber(total);
    }

    regionMapStatus(row) {
        const pct = Number(row?.territorial_coverage_pct || 0);
        if (!Number(row?.communes_total) && !Number(row?.departments_total)) return row?.sections ? "data" : "none";
        if (pct <= 0) return "none";
        if (pct < 25) return "very-low";
        if (pct < 50) return "reinforce";
        if (pct < 75) return "covered";
        return "strong";
    }

    regionMapStatusLabel(row) {
        return {none:"Non couvert", "very-low":"Très faible", reinforce:"À renforcer", covered:"Couverture correcte", strong:"Couverture forte", data:"Données partielles"}[this.regionMapStatus(row)] || "Données partielles";
    }

    regionMapDotStyle(row) {
        return "left:" + Number(row?.map_x || 0) + "%;top:" + Number(row?.map_y || 0) + "%;";
    }

    regionMapDotClass(row) {
        return "kiiraaye-map-dot--" + this.regionMapStatus(row);
    }

    memberElectorGap(row) {
        return Number(row?.member_elector_ratio_pct || 0) - Number(row?.electoral_ratio_pct || 0);
    }

    async openRegionDetail(regionId) {
        this.state.selectedRegionId = Number(regionId) || false;
        await new Promise((resolve) => setTimeout(resolve, 0));

        const target = document.getElementById("kiiraaye-region-detail-" + this.state.selectedRegionId);
        if (target) {
            target.open = true;
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    async openDepartmentDetail(regionId, departmentId) {
        await this.openRegionDetail(regionId);
        await new Promise((resolve) => setTimeout(resolve, 0));

        const target = document.getElementById(
            "kiiraaye-department-detail-" + regionId + "-" + departmentId
        );
        if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    async openCommuneDetail(regionId, departmentId, communeId) {
        const id = Number(communeId) || false;
        if (!id) {
            return;
        }

        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sections de la commune",
            res_model: "kiiraaye.section",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            view_mode: "list,form",
            domain: [["commune_id", "=", id]],
            context: {
                search_default_commune_id: id,
            },
            target: "current",
        });
    }

    memberElectorGapClass(row) {
        const gap = this.memberElectorGap(row);
        if (gap >= 0) {
            return "above";
        }
        if (gap >= -5) {
            return "near";
        }
        if (gap >= -15) {
            return "notable";
        }
        return "large";
    }

    memberElectorGapLabel(row) {
        const gap = this.memberElectorGap(row);
        if (gap >= 0) {
            return "Au-dessus du repère";
        }
        if (gap >= -5) {
            return "Écart faible";
        }
        if (gap >= -15) {
            return "Écart notable";
        }
        return "Écart important";
    }

    get maxDiasporaMembers() {
        return Math.max(
            ...(this.state.data?.diaspora?.countries || []).map((row) => row.members),
            1
        );
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

    electionGapClass(row) {
        return "election-gap--" + (row?.gap_class || "missing");
    }

    electionGapLabel(row) {
        return row?.gap_label || "Donnée non renseignée";
    }

    electionGapValue(row) {
        return row?.gap_pct == null ? "—" : this.formatPercent(row.gap_pct);
    }

    electionValue(value) {
        return value == null ? "—" : this.formatNumber(value);
    }
}

registry.category("actions").add("kiiraaye_dashboard", KiiraayeDashboard);
