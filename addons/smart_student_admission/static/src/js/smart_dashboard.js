/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SmartStudentDashboard extends Component {
    static template = "smart_student_admission.SmartStudentDashboard";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            error: false,
            data: null,
            filters: {
                academic_year_id: false,
                package_id: false,
            },
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
                "smart.dashboard",
                "get_dashboard_data",
                [{ ...this.state.filters }],
            );
        } catch (error) {
            this.state.error = error?.message || "Erreur de chargement du tableau de bord";
        } finally {
            this.state.loading = false;
        }
    }

    async onFilterChange(field, event) {
        const value = event.target.value;
        this.state.filters[field] = value ? Number(value) : false;
        await this.loadDashboard();
    }

    async refresh() {
        await this.loadDashboard();
    }

    formatNumber(value) {
        return new Intl.NumberFormat("fr-FR").format(Number(value) || 0);
    }

    formatPercent(value) {
        return new Intl.NumberFormat("fr-FR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(Number(value) || 0) + " %";
    }

    barWidth(value, max) {
        const denominator = Number(max) || 1;
        return Math.max(4, Math.round((Number(value || 0) / denominator) * 100));
    }

    get maxPackageCount() {
        return Math.max(
            ...(this.state.data?.packages || []).map((item) => Number(item.count || 0)),
            1,
        );
    }
}

registry.category("actions").add("smart_student_dashboard", SmartStudentDashboard);
