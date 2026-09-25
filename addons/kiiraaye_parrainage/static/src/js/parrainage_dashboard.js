/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
export class ParrainageDashboard extends Component {}
ParrainageDashboard.template = "kiiraayeParrainage.Dashboard";
registry.category("actions").add("kiiraaye_parrainage.dashboard", ParrainageDashboard);