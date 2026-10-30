import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillDestroy, useState } from "@odoo/owl";

import { formatSecondsToHms } from "../utils/duration";

const SERVER_ELAPSED_FIELD = "sbs_timer_elapsed_hours";
const SECONDS_PER_HOUR = 3600;

export class SbsTaskTimerField extends Component {
    static template = "sbs_project_extension.SbsTaskTimerField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({ now: Date.now() });
        this.anchor = null;
        this.ticker = setInterval(() => {
            this.state.now = Date.now();
        }, 1000);
        onWillDestroy(() => clearInterval(this.ticker));
    }

    get elapsed() {
        const start = this.props.record.data[this.props.name];
        if (!start || typeof start.toMillis !== "function") {
            this.anchor = null;
            return formatSecondsToHms(0);
        }
        const serverHours = this.props.record.data[SERVER_ELAPSED_FIELD];
        if (serverHours === undefined) {
            return formatSecondsToHms((this.state.now - start.toMillis()) / 1000);
        }
        const serverSeconds = (serverHours || 0) * SECONDS_PER_HOUR;
        if (!this.anchor || this.anchor.serverSeconds !== serverSeconds) {
            this.anchor = { serverSeconds, clientMillis: this.state.now };
        }
        const sinceAnchor = (this.state.now - this.anchor.clientMillis) / 1000;
        return formatSecondsToHms(this.anchor.serverSeconds + sinceAnchor);
    }
}

export const sbsTaskTimerField = {
    component: SbsTaskTimerField,
    displayName: _t("Task Timer"),
    supportedTypes: ["datetime"],
};

registry.category("fields").add("sbs_task_timer", sbsTaskTimerField);
