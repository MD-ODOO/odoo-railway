/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, useRef } from "@odoo/owl";

const HEX_COLOUR_RE = /^#([0-9a-fA-F]{6})$/;

export class LoginThemeColorField extends Component {
    static template = "atliis_login_theme_studio.LoginThemeColorField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.input = useRef("input");
        useInputField({
            getValue: () => this.value,
            parse: (value) => value.trim(),
        });
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get pickerValue() {
        return HEX_COLOUR_RE.test(this.value) ? this.value : "#000000";
    }

    get canUsePicker() {
        return HEX_COLOUR_RE.test(this.value) || !this.value;
    }

    async onPickerInput(event) {
        await this.props.record.update({ [this.props.name]: event.target.value });
    }
}

export const loginThemeColorField = {
    component: LoginThemeColorField,
    displayName: _t("Theme Color"),
    supportedTypes: ["char"],
    extractProps: ({ placeholder }) => ({ placeholder }),
};

registry.category("fields").add("login_theme_color", loginThemeColorField);
