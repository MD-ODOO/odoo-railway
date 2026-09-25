/** @odoo-module **/

import { Component, onMounted, onWillStart, useState } from "@odoo/owl";
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
        onMounted(() => {
            this.renderAdministrativeMap();
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

    departmentMapDotClass(row) {
        return Number(row?.sections || 0) > 0
            ? "kiiraaye-map-dept-dot--covered"
            : "kiiraaye-map-dept-dot--empty";
    }

    departmentMapDotStyle(row) {
        return "left:" + Number(row?.map_x || 0) + "%;top:" + Number(row?.map_y || 0) + "%;";
    }

    normalizeMapName(value) {
        return String(value || "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .replace(/['’\-\s]/g, "");
    }

    mapDepartmentRow(feature) {
        const props = feature?.properties || {};
        const featureName = this.normalizeMapName(props.nom || props.name);
        const featureRegion = String(props.region || props.region_pcode || "");
        const rows = this.state.data?.department_map || [];
        return rows.find((row) =>
            this.normalizeMapName(row.name) === featureName
        ) || null;
    }

    mapDepartmentFill(row) {
        if (!row) return "#E9EFF2";
        return Number(row.sections || 0) > 0 ? "#2D86A6" : "#DCE5E9";
    }

    mapPathFromGeometry(geometry, project) {
        if (!geometry) return "";
        const pathRing = (ring) => ring.map((point, index) => {
            const p = project(point[0], point[1]);
            return (index ? "L" : "M") + p[0].toFixed(2) + "," + p[1].toFixed(2);
        }).join(" ") + " Z";
        if (geometry.type === "Polygon") {
            return geometry.coordinates.map(pathRing).join(" ");
        }
        if (geometry.type === "MultiPolygon") {
            return geometry.coordinates.map((polygon) =>
                polygon.map(pathRing).join(" ")
            ).join(" ");
        }
        return "";
    }

    async renderAdministrativeMap() {
        const host = this.refs?.administrativeMap;
        if (!host || !this.state.data || this.state.sectionScope !== "national") {
            return;
        }
        host.innerHTML = '<div class="kiiraaye-map-loading"><i class="fa fa-spinner fa-spin"/> Chargement du découpage administratif...</div>';
        try {
            const url = "https://galsenapi.lassanasiby.com/api/v1/datasets/sen-admin-boundaries/download/?format=geojson";
            const response = await fetch(url, { headers: { "Accept": "application/geo+json,application/json" } });
            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }
            const geojson = await response.json();
            const features = (geojson.features || []).filter((feature) => {
                const level = String(feature?.properties?.level || feature?.properties?.niveau || "").toLowerCase();
                const name = feature?.properties?.nom || feature?.properties?.name;
                return name && (!level || level.includes("depart"));
            });
            if (!features.length) {
                throw new Error("Aucun polygone départemental trouvé");
            }

            const allPoints = [];
            const collect = (geometry) => {
                const walk = (coords) => {
                    if (!Array.isArray(coords)) return;
                    if (coords.length && typeof coords[0] === "number") {
                        allPoints.push(coords);
                    } else {
                        coords.forEach(walk);
                    }
                };
                walk(geometry?.coordinates);
            };
            features.forEach((feature) => collect(feature.geometry));
            const xs = allPoints.map((p) => p[0]);
            const ys = allPoints.map((p) => p[1]);
            const minX = Math.min(...xs), maxX = Math.max(...xs);
            const minY = Math.min(...ys), maxY = Math.max(...ys);
            const width = 760, height = 610, pad = 18;
            const scale = Math.min(
                (width - pad * 2) / (maxX - minX),
                (height - pad * 2) / (maxY - minY)
            );
            const project = (lon, lat) => [
                pad + (lon - minX) * scale,
                height - pad - (lat - minY) * scale
            ];

            const ns = "http://www.w3.org/2000/svg";
            const svg = document.createElementNS(ns, "svg");
            svg.setAttribute("viewBox", "0 0 " + width + " " + height);
            svg.setAttribute("role", "img");
            svg.setAttribute("aria-label", "Découpage administratif du Sénégal par départements");
            svg.classList.add("kiiraaye-administrative-map-svg");

            features.forEach((feature) => {
                const props = feature.properties || {};
                const row = this.mapDepartmentRow(feature);
                const path = document.createElementNS(ns, "path");
                path.setAttribute("d", this.mapPathFromGeometry(feature.geometry, project));
                path.setAttribute("fill", this.mapDepartmentFill(row));
                path.setAttribute("class", "kiiraaye-map-department-shape");
                path.setAttribute("data-name", props.nom || props.name || "");
                path.setAttribute("title", (props.nom || props.name || "Département") + (row ? " — " + row.sections + " section(s)" : ""));
                if (row) {
                    path.addEventListener("click", () => this.openDepartmentDetail(row.region_id, row.id));
                }
                svg.appendChild(path);
            });

            const labels = features.map((feature) => {
                const row = this.mapDepartmentRow(feature);
                const props = feature.properties || {};
                const points = [];
                const collect = (geometry) => {
                    const walk = (coords) => {
                        if (!Array.isArray(coords)) return;
                        if (coords.length && typeof coords[0] === "number") points.push(coords);
                        else coords.forEach(walk);
                    };
                    walk(geometry?.coordinates);
                };
                collect(feature.geometry);
                if (!points.length) return null;
                const cx = points.reduce((sum,p)=>sum+p[0],0)/points.length;
                const cy = points.reduce((sum,p)=>sum+p[1],0)/points.length;
                const [x,y] = project(cx,cy);
                const text = document.createElementNS(ns, "text");
                text.setAttribute("x", x.toFixed(1));
                text.setAttribute("y", y.toFixed(1));
                text.setAttribute("class", "kiiraaye-map-department-label");
                text.textContent = props.nom || props.name || "";
                return text;
            }).filter(Boolean);
            labels.forEach((label) => svg.appendChild(label));

            host.innerHTML = "";
            host.appendChild(svg);
            const attribution = document.createElement("div");
            attribution.className = "kiiraaye-map-attribution";
            attribution.textContent = "Limites administratives : GalsenAPI / HDX-OCHA COD-AB";
            host.appendChild(attribution);
        } catch (error) {
            host.innerHTML = '<div class="kiiraaye-map-error">Impossible de charger le découpage administratif. ' +
                (error?.message || "") + '</div>';
        }
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
