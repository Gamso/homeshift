import { describe, expect, it } from "vitest";
import {
  Schedule,
  Timeslot,
  daySegments,
  formatMinutes,
  parseTime,
  scheduleEntities,
  schedulesFor,
  slotValue,
} from "../src/schedule/timeline";

const heat = (temperature: number, entity_id = "climate.salon") => ({
  service: "climate.set_temperature",
  entity_id,
  service_data: { temperature },
});

const slot = (start: string, stop: string | null, actions: Timeslot["actions"]): Timeslot => ({
  start,
  stop,
  actions,
});

function schedule(timeslots: Timeslot[], extra: Partial<Schedule> = {}): Schedule {
  return {
    schedule_id: "s",
    entity_id: "switch.schedule_s",
    name: "S",
    enabled: true,
    weekdays: ["daily"],
    tags: ["Maison"],
    timeslots,
    ...extra,
  };
}

/** [start, end, label] of each segment. */
const spans = (s: Schedule) =>
  daySegments(s).map((seg) => [seg.start, seg.end, seg.value.label]);

describe("parseTime / formatMinutes", () => {
  it("reads HH:MM[:SS] as minutes since midnight", () => {
    expect(parseTime("07:30:00")).toBe(450);
    expect(parseTime("7:05")).toBe(425);
    expect(parseTime("00:00:00")).toBe(0);
  });

  it("writes minutes as HH:MM, 24:00 as midnight", () => {
    expect(formatMinutes(450)).toBe("07:30");
    expect(formatMinutes(0)).toBe("00:00");
    expect(formatMinutes(1440)).toBe("00:00");
  });
});

describe("daySegments", () => {
  it("splits a slot that crosses midnight", () => {
    expect(spans(schedule([slot("22:00:00", "06:00:00", [heat(17)])]))).toEqual([
      [0, 360, "17°"],
      [1320, 1440, "17°"],
    ]);
  });

  it("holds a slot without stop until the next one, wrapping around midnight", () => {
    expect(
      spans(
        schedule([
          slot("22:00:00", null, [heat(17)]),
          slot("07:00:00", null, [heat(20)]),
        ]),
      ),
    ).toEqual([
      [0, 420, "17°"],
      [420, 1320, "20°"],
      [1320, 1440, "17°"],
    ]);
  });

  it("covers the whole day with a single slot without stop", () => {
    expect(spans(schedule([slot("06:00:00", null, [heat(19)])]))).toEqual([
      [0, 1440, "19°"],
    ]);
  });

  it("merges back-to-back slots of the same value only", () => {
    expect(
      spans(
        schedule([
          slot("08:00:00", "12:00:00", [heat(20)]),
          slot("12:00:00", "18:00:00", [heat(20)]),
          slot("18:00:00", "22:00:00", [heat(18)]),
        ]),
      ),
    ).toEqual([
      [480, 1080, "20°"],
      [1080, 1320, "18°"],
    ]);
  });

  it("leaves gaps between slots with a stop empty", () => {
    expect(spans(schedule([slot("08:00:00", "10:00:00", [heat(20)])]))).toEqual([
      [480, 600, "20°"],
    ]);
  });

  it("shows only the thermostat slots of a schedule that drives one", () => {
    const s = schedule([
      slot("08:00:00", "10:00:00", [heat(20)]),
      slot("12:00:00", "13:00:00", [{ service: "switch.turn_on", entity_id: "switch.pump" }]),
    ]);
    expect(spans(s)).toEqual([[480, 600, "20°"]]);
    expect(scheduleEntities(s)).toEqual(["climate.salon", "switch.pump"]);
    expect(scheduleEntities(s, true)).toEqual(["climate.salon"]);
  });
});

describe("slotValue", () => {
  const value = (actions: Timeslot["actions"]) => slotValue(slot("08:00:00", null, actions));

  it("reads a setpoint, heating or cooling", () => {
    expect(value([heat(20.5)])).toMatchObject({ kind: "heat", temperature: 20.5, label: "20.5°" });
    expect(
      value([
        {
          service: "climate.set_temperature",
          service_data: { temperature: 26, hvac_mode: "cool" },
        },
      ]),
    ).toMatchObject({ kind: "cool", temperature: 26 });
  });

  it("reads off, presets and HVAC modes", () => {
    expect(
      value([{ service: "climate.set_hvac_mode", service_data: { hvac_mode: "off" } }]),
    ).toMatchObject({ kind: "off", hvacMode: "off" });
    expect(value([{ service: "climate.turn_off" }])).toMatchObject({ kind: "off", label: "off" });
    expect(
      value([{ service: "climate.set_preset_mode", service_data: { preset_mode: "eco" } }]),
    ).toMatchObject({ kind: "preset", preset: "eco" });
    expect(
      value([{ service: "climate.set_hvac_mode", service_data: { hvac_mode: "heat" } }]),
    ).toEqual({ kind: "heat", hvacMode: "heat", label: "heat", entity: undefined });
  });

  it("reads other actions", () => {
    expect(value([{ service: "switch.turn_on" }])).toMatchObject({ kind: "on" });
    expect(value([{ service: "light.toggle" }])).toMatchObject({ kind: "other", label: "toggle" });
    expect(value([])).toEqual({ kind: "other", label: "" });
  });

  it("prefers the thermostat action of a slot", () => {
    expect(value([{ service: "switch.turn_on" }, heat(19)])).toMatchObject({
      kind: "heat",
      temperature: 19,
    });
  });
});

describe("schedulesFor", () => {
  it("keeps the tab's schedules acting on its entities, by name", () => {
    const b = schedule([slot("08:00:00", null, [heat(20)])], { name: "B" });
    const a = schedule([slot("08:00:00", null, [heat(20, "climate.bureau")])], { name: "A" });
    const other = schedule([slot("08:00:00", null, [heat(20)])], { name: "C", tags: ["Travail"] });
    expect(schedulesFor([b, a, other], "Maison", []).map((s) => s.name)).toEqual(["A", "B"]);
    expect(schedulesFor([b, a, other], "Maison", ["climate.bureau"]).map((s) => s.name)).toEqual([
      "A",
    ]);
  });
});
