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
            this.managers = [];
            this.children = [];
            this.self = null;
            this.managersMore = false;
            return;
        }

        let data = await rpc("/kiiraaye/get_org_chart", {
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

        this.managers = data.managers || [];
        this.children = data.children || [];
        this.self = data.self || null;
        this.managersMore = Boolean(data.managers_more);
    }

    async _onOrganisationRedirect(organisationId) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Organisation KIIRAAYE",
            res_model: "kiiraaye.organisation",
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
