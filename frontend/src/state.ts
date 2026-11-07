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

/** Duration label of the card's settings: "25 min", "1h", "1h30". */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m > 0 ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
}
