import { vi } from "vitest";
import { HomeShiftCard } from "../src/components/homeshift-card";
import "../src/components/homeshift-card";

export function entity(entity_id: string, state: string, attributes = {}) {
  return { entity_id, state, attributes };
}

/** States of a fully configured HomeShift integration. */
export function homeshiftStates(): Record<string, any> {
  const list = [
    entity("select.homeshift_day_mode", "Travail", {
      options: ["Maison", "Travail"],
      option_map: { home: "Maison", work: "Travail" },
    }),
    entity("select.homeshift_thermostat_mode", "Chauffage", {
      options: ["Eteint", "Chauffage", "Climatisation"],
      option_map: { off: "Eteint", heating: "Chauffage", cooling: "Climatisation" },
    }),
    entity("number.homeshift_override_duration", "0"),
    entity("number.homeshift_early_switch", "0"),
    entity("sensor.homeshift_next_mode", "Maison"),
    entity("sensor.homeshift_next_mode_at", new Date().toISOString()),
    entity("binary_sensor.homeshift_cover_heat_active", "off"),
    entity("sensor.homeshift_cover_open_time", "08:30"),
    entity("sensor.homeshift_cover_close_time", "21:15"),
    entity("binary_sensor.homeshift_covers_left_open", "off", { covers: [] }),
  ];
  return Object.fromEntries(list.map((e) => [e.entity_id, e]));
}

export function makeHass(states: Record<string, any>, language = "en") {
  return {
    states,
    locale: { language, time_format: "24" },
    language,
    callService: vi.fn().mockResolvedValue(undefined),
  };
}

export async function renderCard(
  hass: any,
  config: Record<string, unknown> = {},
  preview = false,
): Promise<HomeShiftCard> {
  const card = document.createElement("homeshift-card") as HomeShiftCard;
  card.setConfig(config);
  card.preview = preview;
  card.hass = hass;
  document.body.appendChild(card);
  await card.updateComplete;
  return card;
}

export function $(card: HomeShiftCard, selector: string) {
  return card.shadowRoot!.querySelector(selector) as HTMLElement | null;
}

export function $$(card: HomeShiftCard, selector: string) {
  return [...card.shadowRoot!.querySelectorAll(selector)] as HTMLElement[];
}
