import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";

export const appMenuService = {
    dependencies: ["menu"],
    async start(env, {menu}) {
        return {
            getCurrentApp() { return menu.getCurrentApp(); },
            getAppsMenuItems() {
                const apps = computeAppsAndMenuItems(menu.getMenuAsTree("root")).apps;
                const config = JSON.parse(user.settings?.homemenu_config || "null");
                if (config) reorderApps(apps, config);
                return apps;
            },
            selectApp(app) { menu.selectMenu(app); },
        };
    },
};
registry.category("services").add("app_menu", appMenuService);
