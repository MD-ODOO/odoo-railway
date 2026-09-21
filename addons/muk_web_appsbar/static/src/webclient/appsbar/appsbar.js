import { url } from "@web/core/utils/urls";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";

function parseColor(value) {
    if (!value || typeof value !== "string") {
        return null;
    }
    const match = value.trim().match(/^#([0-9a-f]{6})$/i);
    if (!match) {
        return null;
    }
    return [
        parseInt(match[1].slice(0, 2), 16),
        parseInt(match[1].slice(2, 4), 16),
        parseInt(match[1].slice(4, 6), 16),
    ];
}

function getBackgroundPalette(background) {
    const rgb = parseColor(background);
    if (!rgb) {
        return null;
    }

    const [r, g, b] = rgb;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    const hover = rgb.map((value) => Math.round(value + (255 - value) * 0.08));
    const active = rgb.map((value) => Math.round(value * 0.72));
    const accent = luminance > 0.62
        ? rgb.map((value) => Math.round(value * 0.72))
        : rgb.map((value) => Math.min(255, value + 45));

    return {
        background: `rgb(${r}, ${g}, ${b})`,
        hover: `rgb(${hover.join(", ")})`,
        active: `rgb(${active.join(", ")})`,
        accent: `rgb(${accent.join(", ")})`,
        text: luminance > 0.58 ? "#172033" : "#ffffff",
        item: luminance > 0.58 ? `rgb(${active.join(", ")})` : `rgb(${accent.join(", ")})`,
    };
}

export class AppsBar extends Component {
    static template = "muk_web_appsbar.AppsBar";
    static props = {};

    setup() {
        this.appMenuService = useService("app_menu");
        this.sidebarImageUrl = null;

        const background = user.activeCompany.appsbar_background_color || "#172033";
        const root = document.documentElement;
        const colors = getBackgroundPalette(background);

        root.style.setProperty("--mk-appbar-background", background);

        if (colors) {
            root.style.setProperty("--mk-appbar-background", colors.background);
            root.style.setProperty("--mk-appbar-hover-background", colors.hover);
            root.style.setProperty("--mk-appbar-active", colors.active);
            root.style.setProperty("--mk-appbar-accent", colors.accent);
            root.style.setProperty("--mk-appbar-color", colors.text);
            root.style.setProperty("--mk-appbar-hover-item", colors.item);
        }

        if (user.activeCompany.has_appsbar_image) {
            this.sidebarImageUrl = url("/web/image", {
                model: "res.company",
                field: "appbar_image",
                id: user.activeCompany.id,
            });
        }

        const render = () => this.render();
        this.env.bus.addEventListener("MENUS:APP-CHANGED", render);

        onWillUnmount(() => {
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", render);
        });
    }

    _onAppClick(app) {
        return this.appMenuService.selectApp(app);
    }
}
