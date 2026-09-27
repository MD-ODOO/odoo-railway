/** @odoo-module **/
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ParrainageDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ rows: [], loading: true, scope: "all", territorialSlide: 0 });
        this.territorialSlides = ["regional", "departemental", "communal"];
        this.territorialTimer = null;
        onMounted(() => {
            this.territorialTimer = window.setInterval(() => this.nextTerritorialSlide(), 5000);
        });
        onWillUnmount(() => {
            if (this.territorialTimer) {
                window.clearInterval(this.territorialTimer);
                this.territorialTimer = null;
            }
        });
        onWillStart(async () => await this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        const domain = this.state.scope === "all" ? [] : [["scope", "=", this.state.scope]];
        this.state.rows = await this.orm.searchRead(
            "kiiraaye.parrainage.dashboard",
            domain,
            ["scope","location_name","region_name","departement_name","commune_name","parrain_count","cni_count"],
            {order:"parrain_count desc", limit:1000}
        );
        this.state.loading = false;
    }
    async setScope(scope) {
        this.state.scope = scope;
        await this.loadData();
    }
    get total() { return this.state.rows.reduce((s,r)=>s+(r.parrain_count||0),0); }
    get distinctCni() { return this.state.rows.reduce((s,r)=>s+(r.cni_count||0),0); }
    get national() { return this.state.rows.filter(r=>r.scope==="national").reduce((s,r)=>s+(r.parrain_count||0),0); }
    get diaspora() { return this.state.rows.filter(r=>r.scope==="diaspora").reduce((s,r)=>s+(r.parrain_count||0),0); }
    formatLocation(row) {
        return [row.region_name, row.departement_name, row.commune_name].filter(Boolean).join(" · ") || "National";
    }
    get territorialType() { return this.territorialSlides[this.state.territorialSlide]; }
    get territorialTitle() {
        return {
            regional: "Couverture régionale",
            departemental: "Couverture départementale",
            communal: "Couverture communale",
        }[this.territorialType];
    }
    get territorialRows() {
        const groups = new Map();
        const keyField = {
            regional: "region_name",
            departemental: "departement_name",
            communal: "commune_name",
        }[this.territorialType];
        for (const row of this.state.rows) {
            if (row.scope !== "national") continue;
            const key = row[keyField];
            if (!key) continue;
            if (!groups.has(key)) {
                groups.set(key, {
                    name: key,
                    region_name: row.region_name,
                    departement_name: row.departement_name,
                    parrain_count: 0,
                    cni_count: 0,
                });
            }
            const item = groups.get(key);
            item.parrain_count += row.parrain_count || 0;
            item.cni_count += row.cni_count || 0;
        }
        return [...groups.values()]
            .sort((a, b) => b.parrain_count - a.parrain_count)
            .slice(0, 12);
    }
    territorialBarWidth(row) {
        const max = this.territorialRows[0]?.parrain_count || 1;
        return Math.min(100, (row.parrain_count / max) * 100);
    }
    setTerritorialSlide(index) {
        const count = this.territorialSlides.length;
        this.state.territorialSlide = (index + count) % count;
    }
    previousTerritorialSlide() {
        this.setTerritorialSlide(this.state.territorialSlide - 1);
    }
    nextTerritorialSlide() {
        this.setTerritorialSlide(this.state.territorialSlide + 1);
    }
    openList() { this.action.doAction("kiiraaye_parrainage.action_parrainage"); }
    openNationalList() { this.action.doAction("kiiraaye_parrainage.action_parrainage_national"); }
}
ParrainageDashboard.template = "kiiraayeParrainage.Dashboard";
registry.category("actions").add("kiiraaye_parrainage.dashboard", ParrainageDashboard);