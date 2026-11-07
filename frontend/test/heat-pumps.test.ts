import { afterEach, describe, expect, it } from "vitest";
import { $, $$, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

/** The card with its climate section unfolded. */
async function renderOpen(hass: any) {
  const card = await renderCard(hass);
  $(card, ".heat-pumps-head")!.click();
  await card.updateComplete;
  return card;
}

afterEach(() => {
  document.body.innerHTML = "";
});

const SWITCH = "switch.salon_enable_auto_start_stop";

function pump(overrides: Record<string, unknown> = {}) {
  return {
    switch: SWITCH,
    name: "Salon",
    driven: true,
    comfort: false,
    auto_start_stop: true,
    manual: false,
    setpoint: 17.5,
    threshold: 19,
    comfort_when: "above",
    ...overrides,
  };
}

function hassWith(pumps: unknown[], language = "en") {
  const states = homeshiftStates();
  states["sensor.homeshift_auto_start_stop"] = entity("sensor.homeshift_auto_start_stop", "0", {
    climates: pumps,
  });
  return makeHass(states, language);
}

describe("climate auto start/stop", () => {
  it("is hidden without the sensor", async () => {
    const card = await renderCard(makeHass(homeshiftStates()));
    expect($(card, ".heat-pumps")).toBeNull();
  });

  it("shows a climate VTherm may stop, with its setpoint against the threshold", async () => {
    const card = await renderOpen(hassWith([pump()]));
    const row = $(card, ".heat-pump")!;
    expect(row.classList.contains("auto")).toBe(true);
    expect(row.textContent).toContain("Salon");
    expect(row.textContent).toContain("Setpoint 17.5° · may stop below 19°");
    expect($(card, ".heat-pump-tag")!.textContent!.trim()).toBe("Auto");
  });

  it("shows a climate kept running, in French", async () => {
    const card = await renderOpen(
      hassWith([pump({ comfort: true, auto_start_stop: false, setpoint: 20 })], "fr"),
    );
    const row = $(card, ".heat-pump")!;
    expect(row.classList.contains("comfort")).toBe(true);
    expect(row.textContent).toContain("Consigne 20° · tourne dès 19°");
    expect($(card, ".heat-pump-tag")!.textContent!.trim()).toBe("Confort");
  });

  it("reads a cooling threshold the other way round", async () => {
    const running = await renderOpen(
      hassWith([pump({ comfort: true, auto_start_stop: false, setpoint: 23, threshold: 24, comfort_when: "below" })]),
    );
    expect($(running, ".heat-pump-status")!.textContent).toContain("Setpoint 23° · runs up to 24°");
    document.body.innerHTML = "";
    const stoppable = await renderOpen(
      hassWith([pump({ comfort: false, setpoint: 27, threshold: 24, comfort_when: "below" })], "fr"),
    );
    expect($(stoppable, ".heat-pump-status")!.textContent).toContain("arrêt possible au-dessus de 24°");
  });

  it("says when the switch was flipped by hand", async () => {
    const card = await renderOpen(hassWith([pump({ manual: true })]));
    expect($(card, ".heat-pump-manual")!.textContent).toBe("Set by hand");
  });

  it("toggles the switch on a tap", async () => {
    const hass = hassWith([pump()]);
    const card = await renderOpen(hass);
    $(card, ".heat-pump")!.click();
    expect(hass.callService).toHaveBeenCalledWith("switch", "toggle", { entity_id: SWITCH });
  });

  it("leaves a climate not driven in this mode greyed out and inert", async () => {
    const card = await renderOpen(
      hassWith([
        pump({ driven: false, comfort: null, threshold: null, comfort_when: null }),
        pump({ name: "Chambre" }),
      ]),
    );
    const [salon, chambre] = $$(card, ".heat-pump") as HTMLButtonElement[];
    expect(salon.classList.contains("idle")).toBe(true);
    expect(salon.disabled).toBe(true);
    expect(salon.textContent).toContain("Not driven in this thermostat mode");
    expect(chambre.disabled).toBe(false);
  });

  it("says the thermostat is off when it is", async () => {
    const hass = hassWith([pump({ driven: false, comfort: null })]);
    hass.states["select.homeshift_thermostat_mode"] = entity(
      "select.homeshift_thermostat_mode",
      "Eteint",
      hass.states["select.homeshift_thermostat_mode"].attributes,
    );
    const card = await renderOpen(hass);
    expect($(card, ".heat-pump")!.textContent).toContain("Thermostat off: left as it is");
  });

  it("is folded at first, with a summary of the states", async () => {
    const card = await renderCard(
      hassWith([
        pump({ comfort: true }),
        pump({ name: "Chambre" }),
        pump({ name: "Bureau" }),
        pump({ name: "Cave", driven: false, comfort: null }),
      ]),
    );
    const head = $(card, ".heat-pumps-head")!;
    expect(head.getAttribute("aria-expanded")).toBe("false");
    expect($(card, ".heat-pump")).toBeNull();
    expect($(card, ".heat-pumps-summary")!.textContent).toBe("1 Comfort · 2 Auto · 1 not driven");
    head.click();
    await card.updateComplete;
    expect(head.getAttribute("aria-expanded")).toBe("true");
    expect($$(card, ".heat-pump")).toHaveLength(4);
  });

  it("sums up a single climate by its state, and flags a flip by hand", async () => {
    const card = await renderCard(hassWith([pump({ manual: true })], "fr"));
    const summary = $(card, ".heat-pumps-summary")!;
    expect(summary.textContent).toBe("Auto");
    expect($(card, ".heat-pumps-head .manual")!.getAttribute("aria-label")).toBe("Forcé à la main");
  });
});
