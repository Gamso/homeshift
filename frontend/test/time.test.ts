import { afterEach, describe, expect, it, vi } from "vitest";
import {
  daysBetween,
  formatTime,
  secondsOfDay,
  timeFormat,
  timeZone,
} from "../src/time";
import { $, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  vi.useRealTimers();
  document.body.innerHTML = "";
});

describe("next mode time", () => {
  it("rolls Tomorrow over to Today at midnight, without polling", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "Date"] });
    vi.setSystemTime(new Date(2026, 0, 10, 23, 58));
    const states = homeshiftStates();
    states["sensor.homeshift_next_mode_at"] = entity(
      "sensor.homeshift_next_mode_at",
      new Date(2026, 0, 11, 8, 0).toISOString(),
    );
    const card = await renderCard(makeHass(states));
    expect($(card, ".next-row")?.textContent).toContain("Tomorrow ");
    expect(vi.getTimerCount()).toBe(1);

    await vi.advanceTimersByTimeAsync(3 * 60 * 1000);
    await card.updateComplete;
    expect($(card, ".next-row")?.textContent).toContain("Today ");

    card.remove();
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("time format (A-4)", () => {
  const afternoon = new Date(2026, 0, 10, 14, 5);

  it("follows a forced 24 h profile", () => {
    expect(formatTime(afternoon, { language: "en", time_format: "24" })).toBe(
      "14:05",
    );
  });

  it("follows a forced 12 h profile", () => {
    expect(
      formatTime(afternoon, { language: "fr", time_format: "12" }),
    ).toMatch(/02:05\s?PM/i);
  });

  it("uses the HA language, not the browser, by default", () => {
    expect(timeFormat({ language: "fr", time_format: "language" })).toEqual({
      locale: "fr",
      hour12: undefined,
    });
    expect(timeFormat({ language: "fr", time_format: "system" }).locale).toBe(
      undefined,
    );
  });
});

describe("Home Assistant time zone", () => {
  const AUCKLAND = "Pacific/Auckland"; // UTC+13 in January

  it("uses the server's zone unless the profile asks for local", () => {
    const config = { time_zone: AUCKLAND };
    expect(timeZone({ config, locale: { time_zone: "server" } })).toBe(AUCKLAND);
    expect(timeZone({ config, locale: {} })).toBe(AUCKLAND);
    const local = Intl.DateTimeFormat().resolvedOptions().timeZone;
    expect(timeZone({ config, locale: { time_zone: "local" } })).toBe(
      local && local !== "UTC" ? local : AUCKLAND,
    );
    expect(timeZone({})).toBeUndefined();
  });

  it("formats times and counts days in that zone", () => {
    const at = new Date("2026-01-10T20:00:00Z");
    expect(formatTime(at, { language: "en", time_format: "24" }, AUCKLAND)).toBe("09:00");
    expect(secondsOfDay(at, AUCKLAND)).toBe(9 * 3600);
    expect(daysBetween(at, new Date("2026-01-11T05:00:00Z"), AUCKLAND)).toBe(0);
    expect(daysBetween(at, new Date("2026-01-11T12:00:00Z"), AUCKLAND)).toBe(1);
  });

  it("says Today / Tomorrow by the server's calendar", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-01-10T20:00:00Z"));
    const states = homeshiftStates();
    states["sensor.homeshift_next_mode_at"] = entity(
      "sensor.homeshift_next_mode_at",
      "2026-01-11T05:00:00Z",
    );
    const hass = {
      ...makeHass(states),
      config: { time_zone: AUCKLAND },
      locale: { language: "en", time_format: "24", time_zone: "server" },
    };
    const card = await renderCard(hass);
    expect($(card, ".next-row")?.textContent).toContain("Today 18:00");
  });
});
