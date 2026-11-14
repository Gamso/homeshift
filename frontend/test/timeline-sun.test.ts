import { describe, expect, it } from "vitest";
import { Schedule, daySegments, parseTime, sunTimes } from "../src/schedule/timeline";

const heat = (temperature: number) => ({
  service: "climate.set_temperature",
  entity_id: "climate.salon",
  service_data: { temperature },
});

function schedule(timeslots: Schedule["timeslots"]): Schedule {
  return {
    schedule_id: "s",
    entity_id: "switch.schedule_s",
    name: "S",
    enabled: true,
    weekdays: ["daily"],
    tags: ["Maison"],
    timeslots,
  };
}

// Sunrise 08:00, sunset 17:30, in local time.
const SUN = sunTimes({
  attributes: {
    next_rising: new Date(2026, 0, 10, 8, 0).toISOString(),
    next_setting: new Date(2026, 0, 10, 17, 30).toISOString(),
  },
});

describe("sun times in schedules", () => {
  it("reads sunrise and sunset from sun.sun", () => {
    expect(SUN).toEqual({ sunrise: 480, sunset: 1050 });
    expect(sunTimes(undefined)).toEqual({ sunrise: undefined, sunset: undefined });
  });

  it("reads them in the server's time zone when given", () => {
    // 07:15 UTC is 08:15 in Paris in January.
    const sun = sunTimes(
      { attributes: { next_rising: "2026-01-10T07:15:00+00:00", next_setting: "2026-01-10T16:20:00+00:00" } },
      "Europe/Paris",
    );
    expect(sun).toEqual({ sunrise: 495, sunset: 1040 });
  });

  it("resolves sunrise / sunset with an offset", () => {
    expect(parseTime("sunrise", SUN)).toBe(480);
    expect(parseTime("sunrise+00:30:00", SUN)).toBe(510);
    expect(parseTime("sunset-01:00:00", SUN)).toBe(990);
    expect(parseTime("sunrise-09:00:00", SUN)).toBe(1380);
  });

  it("never returns NaN", () => {
    expect(parseTime("sunrise+00:30:00")).toBeUndefined();
    expect(parseTime("noon")).toBeUndefined();
    expect(parseTime("07:30:00")).toBe(450);
  });

  it("draws a sun slot where the sun is", () => {
    const segments = daySegments(
      schedule([
        { start: "sunrise+00:30:00", stop: null, actions: [heat(20)] },
        { start: "sunset", stop: null, actions: [heat(17)] },
      ]),
      SUN,
    );
    expect(segments.map((s) => [s.start, s.end, s.value.temperature])).toEqual([
      [0, 510, 17],
      [510, 1050, 20],
      [1050, 1440, 17],
    ]);
  });

  it("drops only the unresolved slot without sun.sun", () => {
    const segments = daySegments(
      schedule([
        { start: "06:00:00", stop: null, actions: [heat(20)] },
        { start: "sunset", stop: null, actions: [heat(17)] },
        { start: "22:00:00", stop: null, actions: [heat(16)] },
      ]),
    );
    // The 06:00 slot without stop keeps running until the next resolved one.
    expect(segments.map((s) => [s.start, s.end, s.value.temperature])).toEqual([
      [0, 360, 16],
      [360, 1320, 20],
      [1320, 1440, 16],
    ]);
  });
});
