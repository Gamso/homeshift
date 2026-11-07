import { afterEach, describe, expect, it } from "vitest";
import { formatMinutes, isUsable, numericState } from "../src/state";
import { $, $$, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("state helpers", () => {
  it("rejects unknown, unavailable, empty and missing states", () => {
    expect(isUsable(undefined)).toBe(false);
    expect(isUsable("unknown")).toBe(false);
    expect(isUsable({ state: "unavailable" })).toBe(false);
    expect(isUsable({ state: "" })).toBe(false);
    expect(isUsable({ state: "08:30" })).toBe(true);
  });

  it("reads numbers only from usable finite states", () => {
    expect(numericState({ state: "unavailable" })).toBeUndefined();
    expect(numericState({ state: "abc" })).toBeUndefined();
    expect(numericState({ state: "25" })).toBe(25);
  });

  it("formats minutes like the settings labels", () => {
    expect(formatMinutes(25)).toBe("25 min");
    expect(formatMinutes(60)).toBe("1h");
    expect(formatMinutes(90)).toBe("1h30");
  });
});

describe("missing entities (B-3)", () => {
  it("reports a missing entity instead of showing stub data", async () => {
    const states = homeshiftStates();
    delete states["select.homeshift_day_mode"];
    const card = await renderCard(makeHass(states));
    expect($(card, ".error")?.textContent).toContain(
      "Entity not found: select.homeshift_day_mode",
    );
    expect($(card, ".presets")).toBeNull();
  });

  it("uses localized stub data in the card picker preview", async () => {
    const card = await renderCard(makeHass({}, "fr"), {}, true);
    expect($(card, ".error")).toBeNull();
    $(card, '[role="combobox"]')!.click();
    await card.updateComplete;
    const labels = $$(card, '[role="option"]').map((o) => o.textContent!.trim());
    expect(labels).toEqual(["Maison", "Travail", "Télétravail", "Absence"]);
    const selected = $(card, '[role="option"][aria-selected="true"]');
    expect(selected?.textContent?.trim()).toBe("Travail");
    expect($$(card, "button.preset").map((b) => b.textContent!.trim())).toEqual(
      ["Éteint", "Chauffage", "Climatisation", "Ventilation"],
    );
    expect($(card, "button.preset.on")?.textContent?.trim()).toBe("Chauffage");
    expect(card.shadowRoot!.textContent).not.toContain("preview.");
  });

  it("hides a setting whose number entity is missing", async () => {
    const states = homeshiftStates();
    delete states["number.homeshift_early_switch"];
    const card = await renderCard(makeHass(states));
    expect($$(card, ".setting")).toHaveLength(1);
  });
});

describe("unknown / unavailable sensors (B-4)", () => {
  it.each(["unknown", "unavailable"])("hides next mode when %s", async (s) => {
    const states = homeshiftStates();
    states["sensor.homeshift_next_mode"] = entity("sensor.homeshift_next_mode", s);
    states["sensor.homeshift_next_mode_at"] = entity("sensor.homeshift_next_mode_at", s);
    const card = await renderCard(makeHass(states));
    expect($(card, ".next-row")).toBeNull();
    expect(card.shadowRoot!.textContent).not.toContain(s);
  });

  it("hides cover times when unavailable", async () => {
    const states = homeshiftStates();
    states["sensor.homeshift_cover_open_time"].state = "unavailable";
    states["sensor.homeshift_cover_close_time"].state = "unknown";
    const card = await renderCard(makeHass(states));
    expect($(card, ".cover-times")).toBeNull();
  });
});

describe("duration settings (B-5)", () => {
  it("is neither highlighted nor NaN when unavailable", async () => {
    const states = homeshiftStates();
    states["number.homeshift_override_duration"].state = "unavailable";
    const card = await renderCard(makeHass(states));
    const head = $$(card, "button.setting-head")[0] as HTMLButtonElement;
    expect(head.disabled).toBe(true);
    expect($(card, ".setting-value")?.classList.contains("set")).toBe(false);
    expect($(card, ".setting-value")?.textContent).toBe("Unavailable");
    expect(card.shadowRoot!.innerHTML).not.toContain("NaN");
  });

  it("shows a value set outside the presets", async () => {
    const states = homeshiftStates();
    states["number.homeshift_early_switch"].state = "25";
    const card = await renderCard(makeHass(states));
    const value = $$(card, ".setting-value")[1];
    expect(value.textContent).toBe("25 min");
    expect(value.classList.contains("set")).toBe(true);
  });

  it("calls number.set_value with the next preset", async () => {
    const hass = makeHass(homeshiftStates());
    const card = await renderCard(hass);
    $$(card, "button.setting-head")[0].click();
    await card.updateComplete;
    $$(card, ".stepper button")[1].click();
    expect(hass.callService).toHaveBeenCalledWith("number", "set_value", {
      entity_id: "number.homeshift_override_duration",
      value: 15,
    });
  });
});

describe("cover entity (B-2)", () => {
  it("is not part of the stub config", async () => {
    const { HomeShiftCard } = await import("../src/components/homeshift-card");
    expect(HomeShiftCard.getStubConfig()).not.toHaveProperty("cover_entity");
  });

  it("does not act on a configured but missing cover", async () => {
    const hass = makeHass(homeshiftStates());
    const card = await renderCard(hass, { cover_entity: "cover.nope" });
    const row = $(card, ".cover-time")!;
    expect(row.tagName).toBe("SPAN");
    row.click();
    expect(hass.callService).not.toHaveBeenCalled();
  });
});

describe("duration stepper", () => {
  async function stepFrom(state: string, button: 0 | 1) {
    const states = homeshiftStates();
    states["number.homeshift_early_switch"].state = state;
    const hass = makeHass(states);
    const card = await renderCard(hass);
    $$(card, "button.setting-head")[1].click();
    await card.updateComplete;
    $$(card, ".stepper button")[button].click();
    return hass.callService;
  }

  it.each([
    ["25", 1, 30],
    ["25", 0, 15],
    ["45", 1, 60],
    ["45", 0, 30],
  ] as const)("steps from %s min to the adjacent preset", async (state, button, value) => {
    expect(await stepFrom(state, button)).toHaveBeenCalledWith(
      "number",
      "set_value",
      { entity_id: "number.homeshift_early_switch", value },
    );
  });

  it("does not step past the last preset", async () => {
    const states = homeshiftStates();
    states["number.homeshift_early_switch"].state = "300";
    const card = await renderCard(makeHass(states));
    $$(card, "button.setting-head")[1].click();
    await card.updateComplete;
    const [down, up] = $$(card, ".stepper button") as HTMLButtonElement[];
    expect(up.disabled).toBe(true);
    expect(down.disabled).toBe(false);
  });
});
