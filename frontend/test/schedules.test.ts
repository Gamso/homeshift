import { afterEach, describe, expect, it, vi } from "vitest";
import { HomeShiftCard } from "../src/components/homeshift-card";
import { Schedule } from "../src/schedule/timeline";
import { $, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

const heat = (entity_id: string, temperature: number) => ({
  service: "climate.set_temperature",
  entity_id,
  service_data: { temperature, hvac_mode: "heat" },
});

const cool = (entity_id: string, temperature: number) => ({
  service: "climate.set_temperature",
  entity_id,
  service_data: { temperature, hvac_mode: "cool" },
});

function schedules(): Schedule[] {
  return [
    {
      schedule_id: "a1",
      entity_id: "switch.schedule_travail_salon",
      name: "Travail salon",
      enabled: true,
      weekdays: ["daily"],
      tags: ["Travail"],
      timeslots: [
        { start: "00:00:00", stop: "07:00:00", actions: [heat("climate.salon", 18)] },
        { start: "07:00:00", stop: "00:00:00", actions: [heat("climate.salon", 20.5)] },
      ],
    },
    {
      schedule_id: "a2",
      entity_id: "switch.schedule_travail_salon_clim",
      name: "Travail salon clim",
      enabled: false,
      weekdays: ["daily"],
      tags: ["Travail"],
      timeslots: [{ start: "14:00:00", stop: "18:00:00", actions: [cool("climate.salon", 26)] }],
    },
    {
      schedule_id: "b1",
      entity_id: "switch.schedule_maison_bureau",
      name: "Maison bureau",
      enabled: true,
      weekdays: ["daily"],
      tags: ["Maison"],
      timeslots: [{ start: "08:00:00", stop: "18:00:00", actions: [heat("climate.bureau", 20)] }],
    },
  ];
}

function schedulerHass(list: Schedule[] = schedules()) {
  const states = homeshiftStates();
  states["climate.salon"] = entity("climate.salon", "heat", {
    friendly_name: "Salon",
    current_temperature: 19.2,
  });
  states["switch.schedule_travail_salon"] = entity("switch.schedule_travail_salon", "on");
  states["switch.schedule_travail_salon_clim"] = entity(
    "switch.schedule_travail_salon_clim",
    "off",
  );
  return { ...makeHass(states), callWS: vi.fn().mockResolvedValue(list) };
}

async function settle(card: HomeShiftCard) {
  for (let i = 0; i < 3; i++) {
    await card.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
  }
}

async function render(hass: any, config: Record<string, unknown> = {}) {
  const card = await renderCard(hass, config);
  await settle(card);
  return card;
}

type Lit = HTMLElement & { updateComplete: Promise<unknown> };

/** Stands in for scheduler-card, recording the configuration it receives. */
class FakeScheduler extends HTMLElement {
  config: any;
  hass: any;
  setConfig(config: any) {
    this.config = config;
  }
}
if (!customElements.get("scheduler-card")) customElements.define("scheduler-card", FakeScheduler);

/** Shadow root of the panel: the tabs, the edit button, the content. */
async function panel(card: HomeShiftCard) {
  await settle(card);
  const element = $(card, "homeshift-schedule-panel") as Lit;
  await element.updateComplete;
  return element.shadowRoot!;
}

/** Shadow root of the timelines of the shown tab. */
async function timelines(card: HomeShiftCard) {
  const element = (await panel(card)).querySelector("homeshift-schedule-timeline") as Lit;
  await element.updateComplete;
  return element.shadowRoot!;
}

async function open(card: HomeShiftCard) {
  $(card, ".schedules-open")!.click();
  return timelines(card);
}

describe("schedules panel", () => {
  it("shows a bar naming the day mode, panel closed", async () => {
    const card = await render(schedulerHass());
    const bar = $(card, ".schedules-open")!;
    expect(bar.textContent).toContain("Schedules");
    expect(bar.textContent).toContain("Travail");
    expect(bar.getAttribute("aria-expanded")).toBe("false");
    expect($(card, ".schedules-panel")).toBeNull();
  });

  it("stays hidden without the Scheduler integration", async () => {
    const hass = { ...makeHass(homeshiftStates()), callWS: vi.fn().mockRejectedValue(new Error("unknown command")) };
    const card = await render(hass);
    expect($(card, ".schedules-bar")).toBeNull();
  });

  it("stays hidden when no schedule is tagged with a day mode", async () => {
    const list = schedules().map((s) => ({ ...s, tags: ["Other"] }));
    const card = await render(schedulerHass(list));
    expect($(card, ".schedules-bar")).toBeNull();
  });

  it("stays hidden and reads nothing with show_schedules: false", async () => {
    const hass = schedulerHass();
    const card = await render(hass, { show_schedules: false });
    expect($(card, ".schedules-bar")).toBeNull();
    expect(hass.callWS).not.toHaveBeenCalled();
  });

  it("opens over the card with the day mode's rooms", async () => {
    const card = await render(schedulerHass());
    const root = await open(card);
    expect($(card, ".schedules-close")!.getAttribute("aria-expanded")).toBe("true");
    expect($(card, ".container")!.hasAttribute("inert")).toBe(true);
    const rooms = [...root.querySelectorAll(".room-name")].map((r) => r.textContent);
    expect(rooms).toEqual(["Salon"]);
    expect(root.querySelector(".measured")!.textContent).toBe("19.2°");
    // Heating first, then cooling; the disabled one hatched.
    expect([...root.querySelectorAll(".kind")].map((k) => k.getAttribute("icon"))).toEqual([
      "mdi:radiator",
      "mdi:snowflake",
    ]);
    expect(root.querySelectorAll(".row.disabled")).toHaveLength(1);
  });

  it("follows the day mode", async () => {
    const hass = schedulerHass();
    hass.states["select.homeshift_day_mode"] = entity("select.homeshift_day_mode", "Maison", {
      options: ["Maison", "Travail"],
    });
    const card = await render(hass);
    const root = await open(card);
    expect([...root.querySelectorAll(".row")].map((r) => r.getAttribute("title"))).toEqual([
      "Maison bureau",
    ]);
  });

  it("has a tab per day mode, the current one marked and shown", async () => {
    const card = await render(schedulerHass());
    await open(card);
    const root = await panel(card);
    const tabs = [...root.querySelectorAll<HTMLElement>(".tab")];
    expect(tabs.map((t) => t.textContent!.trim())).toEqual(["Maison", "Travail"]);
    expect(tabs[1].getAttribute("aria-selected")).toBe("true");
    expect(tabs[1].querySelector(".active-dot")).not.toBeNull();
    expect(tabs[0].querySelector(".active-dot")).toBeNull();

    tabs[0].click();
    const rows = [...(await timelines(card)).querySelectorAll(".row")];
    expect(rows.map((r) => r.getAttribute("title"))).toEqual(["Maison bureau"]);
  });

  it("swaps the timelines for the scheduler card of the tab", async () => {
    const card = await render(schedulerHass(), { schedule_entities: ["climate.salon"] });
    await open(card);
    const root = await panel(card);
    const edit = root.querySelector<HTMLElement>(".edit")!;
    expect(edit.getAttribute("aria-label")).toBe("Edit schedules");
    edit.click();
    await panel(card);
    await panel(card);
    const scheduler = root.querySelector("scheduler-card") as FakeScheduler;
    expect(scheduler.config).toMatchObject({
      type: "custom:scheduler-card",
      tags: ["Travail"],
      include: ["climate.salon"],
    });
    expect(root.querySelector("homeshift-schedule-timeline")).toBeNull();

    edit.click();
    await panel(card);
    expect(root.querySelector("scheduler-card")).toBeNull();
    expect(root.querySelector("homeshift-schedule-timeline")).not.toBeNull();
  });

  it("keeps only the schedules of schedule_entities", async () => {
    const card = await render(schedulerHass(), { schedule_entities: ["climate.bureau"] });
    const root = await open(card);
    expect(root.querySelector(".empty")!.textContent).toContain("No schedule for Travail");
  });

  it("closes with the bar or Escape, focus back on the bar", async () => {
    const card = await render(schedulerHass());
    await open(card);
    $(card, ".schedules-panel")!.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    await settle(card);
    expect($(card, ".schedules-panel")).toBeNull();
    expect(card.shadowRoot!.activeElement).toBe($(card, ".schedules-open"));

    await open(card);
    $(card, ".schedules-close")!.click();
    await settle(card);
    expect($(card, ".schedules-panel")).toBeNull();
  });

  it("turns the cooling on after turning the heating of the room off", async () => {
    const hass = schedulerHass();
    const card = await render(hass);
    const root = await open(card);
    const [, coolSwitch] = root.querySelectorAll<HTMLElement>(".switch");
    coolSwitch.click();
    await settle(card);
    expect(hass.callService.mock.calls).toEqual([
      ["switch", "turn_off", { entity_id: ["switch.schedule_travail_salon"] }],
      ["switch", "turn_on", { entity_id: "switch.schedule_travail_salon_clim" }],
    ]);
  });

  it("reads the schedules again when a schedule switch changes", async () => {
    const hass = schedulerHass();
    const card = await render(hass);
    expect(hass.callWS).toHaveBeenCalledTimes(1);
    const states = { ...hass.states };
    states["switch.schedule_travail_salon"] = {
      ...states["switch.schedule_travail_salon"],
      state: "off",
      last_updated: "2026-10-10T12:00:00Z",
    };
    card.hass = { ...hass, states };
    await settle(card);
    expect(hass.callWS).toHaveBeenCalledTimes(2);
  });
});
