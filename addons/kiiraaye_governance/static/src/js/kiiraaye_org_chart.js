import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useRecordObserver } from "@web/model/relational_model/utils";


export class KiiraayeOrgChart extends Component {
    static template = "kiiraaye_governance.kiiraaye_org_chart";
    static props = { ...standardFieldProps };

    setup() {
        super.setup();

        this.actionService = useService("action");
        this.state = useState({
            organisationId: null,
            maxLevel: null,
            managers: [],
            children: [],
            self: null,
            managersMore: false,
        });
        this.lastOrganisationId = null;
        this.lastParentId = null;

        useRecordObserver(async (record) => {
            const organisationId = record.resId || false;
            const parentId = record.data.parent_id?.id || false;

            if (
                organisationId !== this.lastOrganisationId
                || parentId !== this.lastParentId
            ) {
                this.lastOrganisationId = organisationId;
                this.lastParentId = parentId;
                this.state.organisationId = organisationId;
                this.state.maxLevel = null;
                await this.fetchOrganisationData(organisationId, parentId);
            }
        });
    }

    async fetchOrganisationData(organisationId, parentId = null) {
        if (!organisationId) {
            this.state.managers = [];
            this.state.children = [];
            this.state.self = null;
            this.state.managersMore = false;
            return;
        }

        const endpoint = this.props.record.resModel === "kiiraaye.section" ? "/kiiraaye/get_section_org_chart" : "/kiiraaye/get_org_chart";

        let data = await rpc(endpoint, {
            organisation_id: organisationId,
            new_parent_id: parentId,
            context: {
                ...user.context,
                max_level: this.state.maxLevel,
            },
        });

        if (!data || Object.keys(data).length === 0) {
            data = {
                managers: [],
                children: [],
                self: null,
                managers_more: false,
            };
        }

        this.state.managers = data.managers || [];
        this.state.children = data.children || [];
        this.state.self = data.self || null;
        this.state.managersMore = Boolean(data.managers_more);
    }

    async _onOrganisationRedirect(organisationId) {
        const resModel = this.props.record.resModel;
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: resModel === "kiiraaye.section" ? "Section / Coordination" : "Organisation KIIRAAYE",
            res_model: resModel,
            res_id: organisationId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async _onMoreManagers() {
        this.state.maxLevel = 100;
        await this.fetchOrganisationData(this.state.organisationId, null);
    }
}


registry.category("fields").add("kiiraaye_org_chart", {
    component: KiiraayeOrgChart,
});
