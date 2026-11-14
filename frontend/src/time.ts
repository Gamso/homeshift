/**
 * Locale and 12/24 h choice for Intl, following the user's Home Assistant
 * profile (hass.locale) rather than the browser:
 * - time_format "12" / "24" forces the hour cycle,
 * - "system" uses the browser locale,
 * - "language" (default) uses the HA language's own convention.
 */
export function timeFormat(hassLocale: any): {
  locale: string | undefined;
  hour12: boolean | undefined;
} {
  const format = hassLocale?.time_format;
  const locale = format === "system" ? undefined : hassLocale?.language;
  const hour12 = format === "12" ? true : format === "24" ? false : undefined;
  return { locale, hour12 };
}

/** Whether the HA profile shows times on a 12 h clock (its own choice, else the locale's). */
export function uses12h(hassLocale: any): boolean {
  const { locale, hour12 } = timeFormat(hassLocale);
  if (hour12 !== undefined) return hour12;
  return new Intl.DateTimeFormat(locale, { hour: "numeric" }).resolvedOptions().hour12 ?? false;
}

/**
 * Clock time of a number of minutes since midnight ("07:30" / "7:30 AM"),
 * in the HA profile's 12 / 24 h format; 24:00 reads as midnight.
 */
export function formatClock(minutes: number, hassLocale: any): string {
  const { locale } = timeFormat(hassLocale);
  const day = 24 * 60;
  const m = ((minutes % day) + day) % day;
  return new Date(Date.UTC(2000, 0, 1, 0, m)).toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    ...(uses12h(hassLocale) ? { hour12: true } : { hourCycle: "h23" }),
  });
}

/**
 * Time zone dates are shown in, as the Home Assistant frontend picks it:
 * the browser's when the profile asks for "local" (and the browser is not
 * on UTC), else the server's (hass.config.time_zone). Undefined (the
 * browser's) when the server does not say.
 */
export function timeZone(hass: any): string | undefined {
  if (hass?.locale?.time_zone === "local") {
    const local = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (local && local !== "UTC") return local;
  }
  return hass?.config?.time_zone || undefined;
}

/** "14:05" / "2:05 PM" according to the HA profile, in `zone`. */
export function formatTime(date: Date, hassLocale: any, zone?: string): string {
  const { locale, hour12 } = timeFormat(hassLocale);
  return date.toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
    hour12,
    timeZone: zone,
  });
}

/** "12 Jan" / "Jan 12" according to the HA language, in `zone`. */
export function formatShortDate(date: Date, hassLocale: any, zone?: string): string {
  const { locale } = timeFormat(hassLocale);
  return date.toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
    timeZone: zone,
  });
}

/** Calendar date and wall-clock time of `date` in `zone`. */
function wallClock(date: Date, zone?: string) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: zone,
      hourCycle: "h23",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
    })
      .formatToParts(date)
      .map((part) => [part.type, Number(part.value)]),
  ) as Record<string, number>;
  return parts;
}

/** Days from `from` to `to`, counted in calendar days of `zone` (0: same day). */
export function daysBetween(from: Date, to: Date, zone?: string): number {
  const day = (date: Date) => {
    const { year, month, day } = wallClock(date, zone);
    return Date.UTC(year, month - 1, day) / 86_400_000;
  };
  return day(to) - day(from);
}

/** Seconds since midnight of `date` in `zone`. */
export function secondsOfDay(date: Date, zone?: string): number {
  const { hour, minute, second } = wallClock(date, zone);
  return hour * 3600 + minute * 60 + second;
}
