import { afterEach, describe, expect, it, vi } from "vitest";
import { formatTime, timeFormat } from "../src/time";
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
