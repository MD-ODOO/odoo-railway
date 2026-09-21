/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);

        let initialized = false;
        const initialize = () => {
            if (initialized) return;

            const appsMenu = document.querySelector(".o_main_navbar .o_navbar_apps_menu");
            if (!appsMenu) return;

            initialized = true;
            appsMenu.classList.add("kiiraaye_apps_bar");

            let closeTimer;
            const open = () => {
                clearTimeout(closeTimer);
                appsMenu.classList.add("kiiraaye_apps_bar_open");
                const toggle = appsMenu.querySelector(".dropdown-toggle");
                if (toggle && !appsMenu.classList.contains("show")) {
                    toggle.click();
                }
            };

            const close = () => {
                clearTimeout(closeTimer);
                closeTimer = setTimeout(() => {
                    appsMenu.classList.remove("kiiraaye_apps_bar_open");
                    const toggle = appsMenu.querySelector(".dropdown-toggle");
                    if (toggle && appsMenu.classList.contains("show")) {
                        toggle.click();
                    }
                }, 180);
            };

            appsMenu.addEventListener("mouseenter", open);
            appsMenu.addEventListener("mouseleave", close);
        };

        const observer = new MutationObserver(initialize);
        observer.observe(document.body, { childList: true, subtree: true });
        initialize();
    },
});
