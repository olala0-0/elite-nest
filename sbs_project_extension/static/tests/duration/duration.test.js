import { expect, test } from "@odoo/hoot";

import {
    formatHoursToHms,
    formatSecondsToHms,
    parseHmsToHours,
} from "@sbs_project_extension/utils/duration";

test.tags("sbs_project_extension_timer");
test("formatSecondsToHms pads every part and rolls over", async () => {
    expect(formatSecondsToHms(0)).toBe("00:00:00");
    expect(formatSecondsToHms(9)).toBe("00:00:09");
    expect(formatSecondsToHms(59)).toBe("00:00:59");
    expect(formatSecondsToHms(60)).toBe("00:01:00");
    expect(formatSecondsToHms(3725)).toBe("01:02:05");
    expect(formatSecondsToHms(360000)).toBe("100:00:00");
});

test.tags("sbs_project_extension_timer");
test("formatSecondsToHms clamps negative and missing values", async () => {
    expect(formatSecondsToHms(-5)).toBe("00:00:00");
    expect(formatSecondsToHms(null)).toBe("00:00:00");
    expect(formatSecondsToHms(undefined)).toBe("00:00:00");
    expect(formatSecondsToHms(0.4)).toBe("00:00:00");
    expect(formatSecondsToHms(0.6)).toBe("00:00:01");
});

test.tags("sbs_project_extension_timer");
test("formatHoursToHms converts hours to a clock string", async () => {
    expect(formatHoursToHms(0)).toBe("00:00:00");
    expect(formatHoursToHms(1)).toBe("01:00:00");
    expect(formatHoursToHms(1.5)).toBe("01:30:00");
    expect(formatHoursToHms(3725 / 3600)).toBe("01:02:05");
    expect(formatHoursToHms(null)).toBe("00:00:00");
});

test.tags("sbs_project_extension_timer");
test("parseHmsToHours accepts hours, hours:minutes and hours:minutes:seconds", async () => {
    expect(parseHmsToHours("")).toBe(0);
    expect(parseHmsToHours("   ")).toBe(0);
    expect(parseHmsToHours(null)).toBe(0);
    expect(parseHmsToHours(undefined)).toBe(0);
    expect(parseHmsToHours("2")).toBe(2);
    expect(parseHmsToHours("0.75")).toBe(0.75);
    expect(parseHmsToHours("1.5")).toBe(1.5);
    expect(parseHmsToHours("0,75")).toBe(0.75);
    expect(parseHmsToHours("01:30")).toBe(1.5);
    expect(parseHmsToHours("01:30:00")).toBe(1.5);
    expect(parseHmsToHours("  01:30:00  ")).toBe(1.5);
    expect(parseHmsToHours("00:00:36")).toBe(0.01);
    expect(parseHmsToHours("100:00:00")).toBe(100);
});

test.tags("sbs_project_extension_timer");
test("parseHmsToHours rejects malformed durations", async () => {
    expect(() => parseHmsToHours("abc")).toThrow();
    expect(() => parseHmsToHours("-1")).toThrow();
    expect(() => parseHmsToHours("1.2.3")).toThrow();
    expect(() => parseHmsToHours("1:2:3:4")).toThrow();
    expect(() => parseHmsToHours("01:60")).toThrow();
    expect(() => parseHmsToHours("01:00:60")).toThrow();
    expect(() => parseHmsToHours("01::00")).toThrow();
});

test.tags("sbs_project_extension_timer");
test("parseHmsToHours round-trips with formatHoursToHms", async () => {
    for (const hours of [0.25, 1, 1.5, 7.75, 100]) {
        expect(parseHmsToHours(formatHoursToHms(hours))).toBe(hours);
    }
});
