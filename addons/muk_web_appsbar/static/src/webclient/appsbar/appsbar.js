import { url } from "@web/core/utils/urls";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";

function getLogoColors(image) {
    try {
        if (!image.naturalWidth || !image.naturalHeight) {
            return null;
        }
        const size = 48;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        ctx.drawImage(image, 0, 0, size, size);
        const data = ctx.getImageData(0, 0, size, size).data;
        const buckets = new Map();

        for (let i = 0; i < data.length; i += 4) {
            const alpha = data[i + 3];
            if (alpha < 80) continue;
            const r = data[i], g = data[i + 1], b = data[i + 2];
            const max = Math.max(r, g, b);
            const min = Math.min(r, g, b);
            if (max - min < 18 || max < 35) continue;

            const key = [Math.round(r / 24) * 24, Math.round(g / 24) * 24, Math.round(b / 24) * 24]
                .map(v => Math.max(0, Math.min(255, v)));
            const k = key.join(",");
            buckets.set(k, (buckets.get(k) || 0) + 1);
        }

        const ranked = [...buckets.entries()].sort((a, b) => b[1] - a[1]);
        if (!ranked.length) return null;

        const [r, g, b] = ranked[0][0].split(",").map(Number);
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        const hover = [r, g, b].map(v => Math.round(v * 0.78));
        const active = [r, g, b].map(v => Math.round(v * 0.62));
        const accent = luminance > 0.62 ? [Math.round(r * 0.75), Math.round(g * 0.75), Math.round(b * 0.75)] : [Math.min(255, r + 35), Math.min(255, g + 35), Math.min(255, b + 35)];

        return {
            background: `rgb(${r}, ${g}, ${b})`,
            hover: `rgb(${hover.join(", ")})`,
            active: `rgb(${active.join(", ")})`,
            accent: `rgb(${accent.join(", ")})`,
            text: luminance > 0.58 ? "#172033" : "#ffffff",
        };
    } catch {
        return null;
    }
}

export class AppsBar extends Component {
    static template = "muk_web_appsbar.AppsBar";
    static props = {};

    setup() {
        this.appMenuService = useService("app_menu");
        this.sidebarImageUrl = null;

        if (user.activeCompany.has_appsbar_image) {
            this.sidebarImageUrl = url("/web/image", {
                model: "res.company",
                field: "appbar_image",
                id: user.activeCompany.id,
            });
        }

        const render = () => this.render();
        this.env.bus.addEventListener("MENUS:APP-CHANGED", render);

        onMounted(() => {
            if (!this.sidebarImageUrl) return;
            const image = new Image();
            image.onload = () => {
                const colors = getLogoColors(image);
                if (!colors) return;
                const root = document.documentElement;
                root.style.setProperty("--mk-appbar-background", colors.background);
                root.style.setProperty("--mk-appbar-hover-background", colors.hover);
                root.style.setProperty("--mk-appbar-active", colors.active);
                root.style.setProperty("--mk-appbar-accent", colors.accent);
                root.style.setProperty("--mk-appbar-color", colors.text);
                root.style.setProperty("--mk-appbar-hover-item", colors.active);
            };
            image.src = this.sidebarImageUrl;
        });

        onWillUnmount(() => this.env.bus.removeEventListener("MENUS:APP-CHANGED", render));
    }

    _onAppClick(app) {
        return this.appMenuService.selectApp(app);
    }
}
