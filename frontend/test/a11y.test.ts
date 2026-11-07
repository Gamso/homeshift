import { afterEach, describe, expect, it } from "vitest";
import { $, $$, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("thermostat presets keyboard access (A-2)", () => {
  it("renders one native button per mode, focusable and activatable", async () => {
    const hass = makeHass(homeshiftStates());
    const card = await renderCard(hass);
    const presets = $$(card, ".presets button.preset") as HTMLButtonElement[];
    expect(presets.map((b) => b.textContent!.trim())).toEqual([
      "Off",
      "Heating",
      "Cooling",
    ]);
    expect(presets.every((b) => !b.disabled && b.tabIndex === 0)).toBe(true);
    expect($(card, ".presets")?.getAttribute("aria-label")).toBe(
      "Thermostat mode",
    );
    expect(presets.map((b) => b.getAttribute("aria-pressed"))).toEqual([
      "false",
      "true",
      "false",
    ]);
    presets[2].click();
    expect(hass.callService).toHaveBeenCalledWith("select", "select_option", {
      entity_id: "select.homeshift_thermostat_mode",
      option: "Climatisation",
    });
  });

  it("disables the presets and highlights none while unavailable", async () => {
    const states = homeshiftStates();
    states["select.homeshift_thermostat_mode"].state = "unavailable";
    const card = await renderCard(makeHass(states));
    const presets = $$(card, "button.preset") as HTMLButtonElement[];
    expect(presets.every((b) => b.disabled)).toBe(true);
    expect($(card, "button.preset.on")).toBeNull();
  });
});

describe("covers left open chip (A-2, B-6)", () => {
  function withCoversLeftOpen(names: string[]) {
    const states = homeshiftStates();
    const ids = names.map((n) => `cover.${n.toLowerCase()}`);
    states["binary_sensor.homeshift_covers_left_open"] = entity(
      "binary_sensor.homeshift_covers_left_open",
      "on",
      { covers: ids },
    );
    names.forEach((n, i) => {
      states[ids[i]] = entity(ids[i], "open", { friendly_name: n });
    });
    return states;
  }

  it("names up to three covers in plain text", async () => {
    const card = await renderCard(makeHass(withCoversLeftOpen(["Salon"])));
    const chip = $(card, ".chip--covers")!;
    expect(chip.tagName).toBe("SPAN");
    expect(chip.textContent).toContain("Not closed: Salon");
  });

  it("reveals the names behind a count on tap, not only on hover", async () => {
    const names = ["Salon", "Cuisine", "Bureau", "Chambre"];
    const card = await renderCard(makeHass(withCoversLeftOpen(names)));
    const chip = $(card, "button.chip--covers")!;
    expect(chip.textContent).toContain("Not closed: 4 covers");
    expect(chip.getAttribute("aria-label")).toBe(
      "Not closed: Salon, Cuisine, Bureau, Chambre",
    );
    expect($(card, ".covers-detail")).toBeNull();
    chip.click();
    await card.updateComplete;
    expect($(card, ".covers-detail")?.textContent).toContain("Chambre");
    expect(chip.getAttribute("aria-expanded")).toBe("true");
  });

  it("shows the heat protection text without hover", async () => {
    const states = homeshiftStates();
    states["binary_sensor.homeshift_cover_heat_active"].state = "on";
    const card = await renderCard(makeHass(states));
    expect($(card, ".chip--heat")?.textContent).toContain(
      "Heat protection active",
    );
    const css = (card.constructor as any).styles.cssText as string;
    expect(css).not.toMatch(/chip--heat\s*\{[^}]*pointer-events:\s*none/);
  });
});

describe("labels", () => {
  it("labels the stepper buttons in French", async () => {
    const card = await renderCard(makeHass(homeshiftStates(), "fr"));
    $$(card, "button.setting-head")[1].click();
    await card.updateComplete;
    expect($(card, ".stepper button")?.getAttribute("aria-label")).toBe(
      "Diminuer : Anticiper les événements",
    );
  });

  it("labels the day mode dropdown", async () => {
    const card = await renderCard(makeHass(homeshiftStates(), "fr"));
    const combobox = $(card, '[role="combobox"]')!;
    expect(combobox.getAttribute("aria-label")).toBe("Mode du jour");
    expect(combobox.getAttribute("aria-expanded")).toBe("false");
  });

  it("picks the day mode from the keyboard", async () => {
    const hass = makeHass(homeshiftStates());
    const card = await renderCard(hass);
    const combobox = $(card, '[role="combobox"]')!;
    const key = async (k: string) => {
      combobox.dispatchEvent(new KeyboardEvent("keydown", { key: k }));
      await card.updateComplete;
    };
    await key("ArrowDown");
    expect(combobox.getAttribute("aria-expanded")).toBe("true");
    expect(combobox.getAttribute("aria-activedescendant")).toBe("day-mode-1");
    await key("ArrowDown");
    expect(combobox.getAttribute("aria-activedescendant")).toBe("day-mode-0");
    await key("Enter");
    expect(hass.callService).toHaveBeenCalledWith("select", "select_option", {
      entity_id: "select.homeshift_day_mode",
      option: "Maison",
    });
    expect(combobox.getAttribute("aria-expanded")).toBe("false");
  });

  it("exposes the collapsible settings as expandable buttons", async () => {
    const card = await renderCard(makeHass(homeshiftStates()));
    const heads = $$(card, "button.setting-head");
    expect(heads).toHaveLength(2);
    expect(heads[0].getAttribute("aria-expanded")).toBe("false");
    heads[0].click();
    await card.updateComplete;
    expect(heads[0].getAttribute("aria-expanded")).toBe("true");
    const [down, up] = $$(card, ".stepper button");
    expect(down.getAttribute("aria-label")).toBe(
      "Decrease: Keep my manual choice",
    );
    expect(up.getAttribute("aria-label")).toBe(
      "Increase: Keep my manual choice",
    );
  });
});
