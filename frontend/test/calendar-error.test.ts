import { afterEach, describe, expect, it } from "vitest";
import { $, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

function hassWith(calendarError: unknown, language = "en") {
  const states = homeshiftStates();
  const day = states["select.homeshift_day_mode"];
  states["select.homeshift_day_mode"] = entity("select.homeshift_day_mode", day.state, {
    ...day.attributes,
    calendar_error: calendarError,
  });
  return makeHass(states, language);
}

describe("calendar error banner", () => {
  it("is hidden while the calendars answer", async () => {
    const card = await renderCard(hassWith(null));
    expect($(card, ".calendar-error")).toBeNull();
  });

  it("names the problem and the day mode kept", async () => {
    const card = await renderCard(hassWith({ since: "2026-11-03T06:12:00+01:00" }));
    const banner = $(card, ".calendar-error")!;
    expect(banner.textContent).toContain("Calendar unreadable");
    expect(banner.textContent).toContain("Day mode kept");
    expect(banner.getAttribute("role")).toBe("alert");
  });

  it("is translated", async () => {
    const card = await renderCard(hassWith({ since: "2026-11-03T06:12:00+01:00" }, "fr"));
    expect($(card, ".calendar-error")!.textContent).toContain("Calendrier illisible");
  });

  it("copes with an unreadable timestamp", async () => {
    const card = await renderCard(hassWith({ since: "nope" }));
    expect($(card, ".calendar-error")).not.toBeNull();
  });
});
