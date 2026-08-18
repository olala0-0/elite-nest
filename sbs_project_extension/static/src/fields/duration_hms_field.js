import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

import { formatHoursToHms, parseHmsToHours } from "../utils/duration";

export class SbsDurationHmsField extends Component {
    static template = "sbs_project_extension.SbsDurationHmsField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            parse: (value) => parseHmsToHours(value),
        });
    }

    get formattedValue() {
        return formatHoursToHms(this.props.record.data[this.props.name]);
    }
}

export const sbsDurationHmsField = {
    component: SbsDurationHmsField,
    displayName: _t("Duration (HH:MM:SS)"),
    supportedTypes: ["float"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
};

registry.category("fields").add("sbs_duration_hms", sbsDurationHmsField);
