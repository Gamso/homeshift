import { localize } from "./localize/localize";

/** States Home Assistant uses when an entity has no meaningful value. */
const UNUSABLE_STATES = new Set(["unknown", "unavailable", ""]);

/**
 * True when the entity exists and carries a real value. Accepts a state
 * object or a raw state string.
 */
export function isUsable(stateObj: { state?: unknown } | string | undefined | null): boolean {
  const state = typeof stateObj === "string" ? stateObj : stateObj?.state;
  return typeof state === "string" && !UNUSABLE_STATES.has(state);
}

/** Numeric value of a number entity, or undefined when it has none. */
export function numericState(stateObj: { state?: unknown } | undefined): number | undefined {
  if (!isUsable(stateObj)) return undefined;
  const value = Number(stateObj!.state);
  return Number.isFinite(value) ? value : undefined;
}

/** Duration label of the card's settings in the user's language: "25 min", "1h", "1h 30m" / "1h30". */
export function formatMinutes(minutes: number, hass?: any): string {
  if (minutes < 60) {
    return localize(hass, "card.duration_minutes", { minutes: String(minutes) });
  }
  const hours = String(Math.floor(minutes / 60));
  const m = Math.round(minutes % 60);
  return m > 0
    ? localize(hass, "card.duration_hours_minutes", {
        hours,
        minutes: String(m).padStart(2, "0"),
      })
    : localize(hass, "card.duration_hours", { hours });
}
