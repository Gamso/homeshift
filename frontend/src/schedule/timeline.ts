/** A schedule as returned by the scheduler component's `scheduler` websocket command. */
export interface Schedule {
  schedule_id: string;
  entity_id: string;
  name: string;
  enabled: boolean;
  weekdays: string[];
  tags?: string[];
  timeslots: Timeslot[];
}

export interface Timeslot {
  start: string;
  stop: string | null;
  actions: { service: string; entity_id?: string; service_data?: Record<string, any> }[];
}

export type ValueKind = "heat" | "cool" | "preset" | "off" | "on" | "other";

/** What a timeslot sets its entity to. */
export interface SlotValue {
  kind: ValueKind;
  /** Entity of the action the value comes from. */
  entity?: string;
  temperature?: number;
  /** Preset set by `climate.set_preset_mode` ("comfort", "eco"...). */
  preset?: string;
  /** HVAC mode set without a temperature ("off", "heat"...). */
  hvacMode?: string;
  /**
   * Raw text of the value ("20°", "comfort", "off"...); the card shows
   * temperatures, presets and modes in the user's language instead.
   */
  label: string;
}

/** Part of the day, in minutes since midnight, during which a value applies. */
export interface Segment {
  start: number;
  end: number;
  value: SlotValue;
}

export const DAY_MINUTES = 24 * 60;

/** "07:30:00" → 450. */
export function parseTime(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + (m || 0);
}

/** "HH:MM" of a number of minutes since midnight. */
export function formatMinutes(minutes: number): string {
  const m = minutes % DAY_MINUTES;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

const isClimate = (action: Timeslot["actions"][number]) => action.service.startsWith("climate.");

/** Whether a schedule drives a thermostat: its timeline then shows only the thermostat. */
function drivesClimate(schedule: Schedule): boolean {
  return schedule.timeslots.some((slot) => slot.actions.some(isClimate));
}

/** Value set by a timeslot, from its first thermostat action, else its first action. */
export function slotValue(slot: Timeslot): SlotValue {
  const action = slot.actions?.find(isClimate) ?? slot.actions?.[0];
  if (!action) return { kind: "other", label: "" };
  const [, service] = action.service.split(".");
  const data = action.service_data ?? {};
  const entity = action.entity_id;
  const mode = data.hvac_mode;
  if (mode === "off") return { kind: "off", entity, hvacMode: mode, label: mode };
  if (service === "turn_off") return { kind: "off", entity, label: "off" };
  if (typeof data.temperature === "number") {
    return {
      kind: mode === "cool" ? "cool" : "heat",
      entity,
      temperature: data.temperature,
      label: `${data.temperature}°`,
    };
  }
  if (data.preset_mode != null) {
    const preset = String(data.preset_mode);
    return { kind: "preset", entity, preset, label: preset };
  }
  if (mode) return { kind: mode === "cool" ? "cool" : "heat", entity, hvacMode: mode, label: mode };
  if (service === "turn_on") return { kind: "on", entity, label: "on" };
  return { kind: "other", entity, label: service ?? action.service };
}

/**
 * Segments of the day a schedule covers. A timeslot with a stop time spans
 * start → stop (across midnight if stop is earlier); a timeslot without one
 * is a single action whose value holds until the next timeslot, wrapping
 * around midnight.
 */
export function daySegments(schedule: Schedule): Segment[] {
  const climate = drivesClimate(schedule);
  const slots = schedule.timeslots
    .filter((slot) => !climate || slot.actions.some(isClimate))
    .map((slot) => ({ slot, start: parseTime(slot.start) }))
    .sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];

  slots.forEach(({ slot, start }, i) => {
    const value = slotValue(slot);
    let end: number;
    if (slot.stop != null) {
      end = parseTime(slot.stop);
      if (end <= start) end += DAY_MINUTES;
    } else {
      const next = slots[(i + 1) % slots.length].start;
      end = next > start ? next : next + DAY_MINUTES;
    }
    if (end > DAY_MINUTES) {
      segments.push({ start, end: DAY_MINUTES, value });
      if (end - DAY_MINUTES > 0) segments.push({ start: 0, end: end - DAY_MINUTES, value });
    } else {
      segments.push({ start, end, value });
    }
  });

  return mergeSegments(
    segments.filter((s) => s.end > s.start).sort((a, b) => a.start - b.start),
  );
}

/** Whether two values set the same thing. */
export function sameValue(a: SlotValue, b: SlotValue): boolean {
  return (
    a.kind === b.kind &&
    a.temperature === b.temperature &&
    a.preset === b.preset &&
    a.hvacMode === b.hvacMode &&
    a.label === b.label
  );
}

/** Joins back-to-back segments of the same value ("Eco | Eco" → "Eco"). */
function mergeSegments(segments: Segment[]): Segment[] {
  const merged: Segment[] = [];
  for (const segment of segments) {
    const last = merged[merged.length - 1];
    if (last && last.end === segment.start && sameValue(last.value, segment.value)) {
      last.end = segment.end;
    } else {
      merged.push({ ...segment });
    }
  }
  return merged;
}

/**
 * Entities a schedule acts on. With `shown`, only those of its timeline:
 * its thermostats when it drives some.
 */
export function scheduleEntities(schedule: Schedule, shown = false): string[] {
  const climate = shown && drivesClimate(schedule);
  const ids = schedule.timeslots.flatMap((slot) =>
    slot.actions
      .filter((a) => !climate || isClimate(a))
      .map((a) => a.entity_id)
      .filter((id): id is string => !!id),
  );
  return [...new Set(ids)];
}

/** Schedules of a tab: tagged with its tag, and acting on its entities when it has some. */
export function schedulesFor(schedules: Schedule[], tag: string, entities: string[]): Schedule[] {
  return schedules
    .filter((s) => s.tags?.includes(tag))
    .filter((s) => !entities.length || scheduleEntities(s).some((e) => entities.includes(e)))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Segment background and text colors: warmer for higher setpoints. */
export function segmentColors(value: SlotValue): { background: string; color: string } {
  switch (value.kind) {
    case "cool":
      return { background: "#378ADD", color: "#fff" };
    case "off":
      return { background: "#353B43", color: "#C3C8D0" };
    case "on":
      return { background: "#1D9E75", color: "#fff" };
    case "other":
      return { background: "#888780", color: "#fff" };
    case "preset":
      return presetColors(value.preset ?? "");
  }
  const t = value.temperature ?? 19;
  if (t < 15) return { background: "#85B7EB", color: "#042C53" };
  if (t < 17.5) return { background: "#FAC775", color: "#412402" };
  if (t < 19.5) return { background: "#EF9F27", color: "#412402" };
  if (t < 21) return { background: "#D85A30", color: "#fff" };
  return { background: "#A32D2D", color: "#fff" };
}

/**
 * Preset colors on the same scale as the setpoints: frost and away are
 * cold, eco mild, comfort warm, boost hot (Versatile Thermostat and the
 * presets Home Assistant defines).
 */
function presetColors(preset: string): { background: string; color: string } {
  const p = preset.toLowerCase();
  if (/frost|hors|away|absen|vacation/.test(p)) return { background: "#85B7EB", color: "#042C53" };
  if (/eco|sleep|night|nuit/.test(p)) return { background: "#FAC775", color: "#412402" };
  if (/boost/.test(p)) return { background: "#A32D2D", color: "#fff" };
  if (/comfort|confort|home|activity/.test(p)) return { background: "#EF9F27", color: "#412402" };
  return { background: "#B4B2A9", color: "#2C2C2A" };
}
