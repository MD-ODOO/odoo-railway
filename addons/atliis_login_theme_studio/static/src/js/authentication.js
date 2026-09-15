/** @odoo-module **/

const AUTH_FORM_SELECTOR = ".oe_login_form, .oe_signup_form, .oe_reset_password_form";

function updatePasswordButton(button, input) {
    const visible = input.type === "text";
    button.setAttribute("aria-pressed", visible ? "true" : "false");
    button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
    button.setAttribute("title", visible ? "Hide password" : "Show password");
    const icon = button.querySelector("i");
    if (icon) {
        icon.classList.toggle("fa-eye", !visible);
        icon.classList.toggle("fa-eye-slash", visible);
    }
}

document.addEventListener("click", (event) => {
    const button = event.target.closest(".o_show_password");
    if (!button) {
        return;
    }
    const input = button.closest(".input-group")?.querySelector("input[type='password'], input[type='text']");
    if (!input || !["password", "text"].includes(input.type)) {
        return;
    }
    input.type = input.type === "password" ? "text" : "password";
    updatePasswordButton(button, input);
    input.focus();
});

document.addEventListener("keydown", (event) => {
    if (!event.target.matches("input[type='password'], input[type='text']")) {
        return;
    }
    const warning = event.target.closest(AUTH_FORM_SELECTOR)?.querySelector(".o_login_theme_caps_lock");
    if (!warning || typeof event.getModifierState !== "function") {
        return;
    }
    const isOn = event.getModifierState("CapsLock");
    warning.classList.toggle("visually-hidden", !isOn);
});

document.addEventListener("keyup", (event) => {
    if (!event.target.matches("input[type='password'], input[type='text']")) {
        return;
    }
    const warning = event.target.closest(AUTH_FORM_SELECTOR)?.querySelector(".o_login_theme_caps_lock");
    if (!warning || typeof event.getModifierState !== "function") {
        return;
    }
    const isOn = event.getModifierState("CapsLock");
    warning.classList.toggle("visually-hidden", !isOn);
});

document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form.matches(AUTH_FORM_SELECTOR)) {
        return;
    }
    const button = form.querySelector("button[type='submit']");
    if (button && !button.disabled) {
        button.disabled = true;
        button.classList.add("disabled");
        button.setAttribute("aria-disabled", "true");
    }
});
