/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ParrainageDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ rows: [], loading: true, scope: "all" });
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
    openList() { this.action.doAction("kiiraaye_parrainage.action_parrainage"); }
    openNationalList() { this.action.doAction("kiiraaye_parrainage.action_parrainage_national"); }
}
ParrainageDashboard.template = "kiiraayeParrainage.Dashboard";
registry.category("actions").add("kiiraaye_parrainage.dashboard", ParrainageDashboard);