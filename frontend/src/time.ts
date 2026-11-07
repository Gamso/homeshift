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

/** "14:05" / "2:05 PM" according to the HA profile. */
export function formatTime(date: Date, hassLocale: any): string {
  const { locale, hour12 } = timeFormat(hassLocale);
  return date.toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
    hour12,
  });
}

/** "12 Jan" / "Jan 12" according to the HA language. */
export function formatShortDate(date: Date, hassLocale: any): string {
  const { locale } = timeFormat(hassLocale);
  return date.toLocaleDateString(locale, { month: "short", day: "numeric" });
}
