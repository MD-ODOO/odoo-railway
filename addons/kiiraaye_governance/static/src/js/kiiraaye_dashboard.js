/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
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
            mapZoom: 1,
            coverageSlideIndex: 0,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
        this.administrativeMapRef = useRef("administrativeMap");
        this.mapDragging = false;
        onMounted(() => {
            this.renderAdministrativeMap();
            this.startCoverageCarousel();
        });
        onWillUnmount(() => {
            this.stopCoverageCarousel();
        });
    }

    startCoverageCarousel() {
        this.stopCoverageCarousel();
        this.coverageCarouselTimer = setInterval(() => {
            if (!this.state.loading) {
                this.nextCoverageCard();
            }
        }, 5000);
    }

    stopCoverageCarousel() {
        if (this.coverageCarouselTimer) {
            clearInterval(this.coverageCarouselTimer);
            this.coverageCarouselTimer = null;
        }
    }

    nextCoverageCard() {
        this.state.coverageSlideIndex =
            (this.state.coverageSlideIndex + 1) % 3;
    }

    previousCoverageCard() {
        this.state.coverageSlideIndex =
            (this.state.coverageSlideIndex + 2) % 3;
    }

    selectCoverageCard(index) {
        const value = Math.max(0, Math.min(2, Number(index) || 0));
        this.state.coverageSlideIndex = value;
        this.startCoverageCarousel();
    }

    get coverageSlideNumber() {
        return this.state.coverageSlideIndex + 1;
    }

    get coverageCurrentLabel() {
        return ["Régional", "Départemental", "Communal"][this.state.coverageSlideIndex] || "Régional";
    }

    get coverageRegions() {
        return this.state.data?.section_geography_overview || [];
    }

    get coverageDepartments() {
        const rows = [];
        for (const region of this.coverageRegions) {
            for (const department of region.departments_rows || []) {
                rows.push({
                    ...department,
                    region_id: region.id,
                    region_name: region.name,
                });
            }
        }
        return rows;
    }

    get coverageCommunes() {
        const rows = [];
        for (const region of this.coverageRegions) {
            for (const department of region.departments_rows || []) {
                for (const commune of department.commune_rows || []) {
                    rows.push({
                        ...commune,
                        region_id: region.id,
                        region_name: region.name,
                        department_id: department.id,
                        department_name: department.name,
                    });
                }
            }
        }
        return rows;
    }

    get coverageRegionStats() {
        const scope = this.state.data?.geography_scope?.regions || {};
        return {
            occupied: Number(scope.occupied || 0),
            total: Number(scope.total || this.coverageRegions.length || 0),
        };
    }

    get coverageDepartmentStats() {
        const scope = this.state.data?.geography_scope?.departments || {};
        return {
            occupied: Number(scope.occupied || 0),
            total: Number(scope.total || this.coverageDepartments.length || 0),
        };
    }

    get coverageCommuneStats() {
        const scope = this.state.data?.geography_scope?.communes || {};
        return {
            occupied: Number(scope.occupied || 0),
            total: Number(scope.total || this.coverageCommunes.length || 0),
        };
    }

    coverageRowClass(occupied, total) {
        return "kiiraaye-coverage-row--" + this.coverageClass(occupied, total);
    }

    coverageBarWidth(occupied, total) {
        const ratio = this.coveragePercent(occupied, total);
        return Math.max(0, Math.min(100, Math.round(ratio)));
    }

    coverageItemStatus(sections) {
        return Number(sections || 0) > 0 ? "covered" : "empty";
    }

    coverageItemStatusLabel(sections) {
        return Number(sections || 0) > 0 ? "Couvert" : "À couvrir";
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
        return Number(row.sections || 0) > 0 ? "#2D86A6" : "#E53935";
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

    mapZoomIn() {
        this.state.mapZoom = Math.min(2.5, this.state.mapZoom + 0.2);
        this.applyMapTransform();
    }

    mapZoomOut() {
        this.state.mapZoom = Math.max(0.7, this.state.mapZoom - 0.2);
        this.applyMapTransform();
    }

    get zoomPercent() {
        return Math.round(this.state.mapZoom * 100);
    }

    mapZoomReset() {
        this.state.mapZoom = 1;
        this.applyMapTransform();
    }

    applyMapTransform() {
        const host = this.administrativeMapRef?.el;
        if (host) {
            host.style.transform = "scale(" + this.state.mapZoom + ")";
        }
    }

    async renderAdministrativeMap() {
        const host = this.administrativeMapRef?.el;
        if (!host) {
            return;
        }

        try {
            const response = await fetch(
                "/kiiraaye_governance/static/src/img/senegal_departments.svg?v=19.0.2.22.65",
                { headers: { "Accept": "image/svg+xml" }, cache: "force-cache" }
            );
            if (!response.ok) {
                throw new Error("Carte SVG introuvable (" + response.status + ")");
            }

            const svgText = await response.text();
            host.innerHTML = svgText;

            const svg = host.querySelector("svg");
            if (!svg) {
                throw new Error("SVG administratif invalide");
            }

            svg.classList.add("kiiraaye-administrative-map-svg");
            this.mapZoom = 1;

            const rows = (this.state.data.department_map || []).map((row) => ({
                ...row,
                _name: this.normalizeMapName(row.name),
            }));

            const rowByName = new Map(rows.map((row) => [row._name, row]));

            host.querySelectorAll(".kiiraaye-map-department-shape").forEach((shape) => {
                const name = this.normalizeMapName(shape.dataset.name || "");
                const code = shape.dataset.code || "";
                const row = rowByName.get(name);

                shape.setAttribute("fill", this.mapDepartmentFill(row));
                const sections = Number(row?.sections || 0);
                if (sections === 0) {
                    shape.classList.add("kiiraaye-map-department-shape--blink");
                } else {
                    shape.classList.add("kiiraaye-map-department-shape--covered");
                }
                shape.setAttribute("tabindex", "0");
                shape.setAttribute("role", "button");
                shape.setAttribute("aria-label", row?.name || shape.dataset.name || code);

                const open = () => {
                    if (row) {
                        this.openDepartmentDetail(row.region_id, row.id);
                    }
                };

                shape.addEventListener("click", open);
                shape.addEventListener("keydown", (event) => {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        open();
                    }
                });
            });

            const attribution = document.createElement("div");
            attribution.className = "kiiraaye-map-attribution";
            attribution.textContent = "Limites administratives — carte locale optimisée";
            host.appendChild(attribution);
        } catch (error) {
            console.error("Kiiraaye: impossible de charger la carte administrative", error);
            // Secours : afficher directement le SVG comme image. Cela garantit
            // que la carte reste visible même si le navigateur bloque le fetch
            // du fichier SVG ou si les assets Odoo sont encore en cache.
            host.innerHTML = "";
            const image = document.createElement("img");
            image.className = "kiiraaye-administrative-map-svg";
            image.alt = "Carte administrative du Sénégal";
            image.src =
                "/kiiraaye_governance/static/src/img/senegal_departments.svg?v=19.0.2.22.65";
            image.onerror = () => {
                host.innerHTML =
                    '<div class="kiiraaye-map-error">Impossible de charger la carte administrative.</div>';
            };
            host.appendChild(image);
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
