import { expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

import "@sbs_project_extension/fields/duration_hms_field";

class TimesheetLog extends models.Model {
    _name = "sbs.timesheet.log";
    _records = [{ id: 1, hours: 1.5, measured_hours: 3725 / 3600 }];
    hours = fields.Float();
    measured_hours = fields.Float();
}

defineMailModels();
defineModels({ TimesheetLog });

onRpc("has_group", () => true);

test.tags("sbs_project_extension_timer");
test("readonly duration renders as a clock string", async () => {
    await mountView({
        type: "form",
        resModel: "sbs.timesheet.log",
        resId: 1,
        arch: `
            <form>
                <field name="measured_hours" widget="sbs_duration_hms" readonly="1"/>
            </form>
        `,
    });

    expect("[name='measured_hours'] input").toHaveCount(0);
    expect("[name='measured_hours']").toHaveText("01:02:05");
});

test.tags("sbs_project_extension_timer");
test("editable duration shows a clock string in an input", async () => {
    await mountView({
        type: "form",
        resModel: "sbs.timesheet.log",
        resId: 1,
        arch: `<form><field name="hours" widget="sbs_duration_hms"/></form>`,
    });

    expect("[name='hours'] input").toHaveCount(1);
    expect("[name='hours'] input").toHaveValue("01:30:00");
});

test.tags("sbs_project_extension_timer");
test("editing a duration parses HH:MM:SS back into hours", async () => {
    let saved;
    onRpc("sbs.timesheet.log", "web_save", ({ args }) => {
        saved = args[1].hours;
    });

    await mountView({
        type: "form",
        resModel: "sbs.timesheet.log",
        resId: 1,
        arch: `<form><field name="hours" widget="sbs_duration_hms"/></form>`,
    });

    await contains("[name='hours'] input").edit("00:45:30");
    await contains(".o_form_button_save").click();

    expect(saved).toBeCloseTo(0.7583333, { digits: 6 });
});

test.tags("sbs_project_extension_timer");
test("an unparsable duration marks the field invalid instead of throwing", async () => {
    await mountView({
        type: "form",
        resModel: "sbs.timesheet.log",
        resId: 1,
        arch: `<form><field name="hours" widget="sbs_duration_hms"/></form>`,
    });

    await contains("[name='hours'] input").edit("not a duration");

    expect(".o_field_invalid, .o_notification").toHaveCount(1);
});
