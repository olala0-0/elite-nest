import { expect, test } from "@odoo/hoot";
import { advanceTime, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

import "@sbs_project_extension/fields/task_timer_field";

const SERVER_ELAPSED_HOURS = 3725 / 3600;

class ProjectTask extends models.Model {
    _name = "project.task";
    _records = [
        {
            id: 1,
            name: "Running task",
            sbs_timer_start: "2026-08-15 09:00:00",
            sbs_timer_elapsed_hours: SERVER_ELAPSED_HOURS,
        },
        { id: 2, name: "Idle task", sbs_timer_start: false, sbs_timer_elapsed_hours: 0 },
    ];
    name = fields.Char();
    sbs_timer_start = fields.Datetime();
    sbs_timer_elapsed_hours = fields.Float();
}

defineMailModels();
defineModels({ ProjectTask });

onRpc("has_group", () => true);

const ARCH = `
    <form>
        <field name="name"/>
        <field name="sbs_timer_start" widget="sbs_task_timer"/>
    </form>
`;

const ARCH_WITH_SERVER_ELAPSED = `
    <form>
        <field name="name"/>
        <field name="sbs_timer_elapsed_hours" invisible="1"/>
        <field name="sbs_timer_start" widget="sbs_task_timer"/>
    </form>
`;

test.tags("sbs_project_extension_timer");
test("running timer renders the elapsed time as HH:MM:SS", async () => {
    mockTimeZone(0);
    mockDate("2026-08-15 10:02:05");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 1,
        arch: ARCH,
    });

    expect(".o_sbs_task_timer").toHaveCount(1);
    expect(".o_sbs_task_timer_value").toHaveText("01:02:05");
});

test.tags("sbs_project_extension_timer");
test("running timer keeps counting while it is displayed", async () => {
    mockTimeZone(0);
    mockDate("2026-08-15 09:00:00");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 1,
        arch: ARCH,
    });

    expect(".o_sbs_task_timer_value").toHaveText("00:00:00");

    await advanceTime(5000);

    expect(".o_sbs_task_timer_value").toHaveText("00:00:05");
});

test.tags("sbs_project_extension_timer");
test("timer widget renders zero instead of crashing without a start value", async () => {
    mockTimeZone(0);
    mockDate("2026-08-15 10:00:00");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 2,
        arch: ARCH,
    });

    expect(".o_sbs_task_timer").toHaveCount(1);
    expect(".o_sbs_task_timer_value").toHaveText("00:00:00");
});

test.tags("sbs_project_extension_timer");
test("timer widget is timezone independent", async () => {
    mockTimeZone(4);
    mockDate("2026-08-15 10:02:05");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 1,
        arch: ARCH,
    });

    expect(".o_sbs_task_timer_value").toHaveText("01:02:05");
});

test.tags("sbs_project_extension_timer");
test("a skewed workstation clock does not shift the counted time", async () => {
    mockTimeZone(0);
    mockDate("2026-08-15 12:30:00");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 1,
        arch: ARCH_WITH_SERVER_ELAPSED,
    });

    expect(".o_sbs_task_timer_value").toHaveText("01:02:05");
});

test.tags("sbs_project_extension_timer");
test("a skewed workstation clock still ticks forward one second at a time", async () => {
    mockTimeZone(0);
    mockDate("2026-08-15 12:30:00");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 1,
        arch: ARCH_WITH_SERVER_ELAPSED,
    });

    expect(".o_sbs_task_timer_value").toHaveText("01:02:05");

    await advanceTime(5000);

    expect(".o_sbs_task_timer_value").toHaveText("01:02:10");
});

test.tags("sbs_project_extension_timer");
test("a backwards-skewed workstation clock does not clamp the counted time to zero", async () => {
    mockTimeZone(0);
    mockDate("2026-08-15 08:00:00");

    await mountView({
        type: "form",
        resModel: "project.task",
        resId: 1,
        arch: ARCH_WITH_SERVER_ELAPSED,
    });

    expect(".o_sbs_task_timer_value").toHaveText("01:02:05");
});
