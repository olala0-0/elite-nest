const SECONDS_PER_HOUR = 3600;

export function formatSecondsToHms(seconds) {
    const total = Math.max(0, Math.round(seconds || 0));
    const hours = Math.floor(total / SECONDS_PER_HOUR);
    const minutes = Math.floor((total % SECONDS_PER_HOUR) / 60);
    const rest = total % 60;
    return [hours, minutes, rest]
        .map((part) => String(part).padStart(2, "0"))
        .join(":");
}

export function formatHoursToHms(hours) {
    return formatSecondsToHms((hours || 0) * SECONDS_PER_HOUR);
}

export function parseHmsToHours(value) {
    const trimmed = String(value === undefined || value === null ? "" : value).trim();
    if (!trimmed) {
        return 0;
    }
    const parts = trimmed.split(":");
    if (parts.length > 3) {
        throw new Error(`"${value}" is not a valid duration`);
    }
    if (parts.length === 1) {
        if (!/^\d+([.,]\d+)?$/.test(trimmed)) {
            throw new Error(`"${value}" is not a valid duration`);
        }
        return Number(trimmed.replace(",", "."));
    }
    const numbers = parts.map((part) => {
        const cleaned = part.trim();
        if (!/^\d+$/.test(cleaned)) {
            throw new Error(`"${value}" is not a valid duration`);
        }
        return Number(cleaned);
    });
    while (numbers.length < 3) {
        numbers.push(0);
    }
    const [hours, minutes, seconds] = numbers;
    if (parts.length > 1 && (minutes > 59 || seconds > 59)) {
        throw new Error(`"${value}" is not a valid duration`);
    }
    return (hours * SECONDS_PER_HOUR + minutes * 60 + seconds) / SECONDS_PER_HOUR;
}
