import { afterEach, describe, expect, it } from "vitest";
import { entity, homeshiftStates, makeHass, renderCard } from "./helpers";
import { discoverEntities } from "../src/entities";

afterEach(() => {
  document.body.innerHTML = "";
});

const registry = (id: string, key: string, platform = "homeshift") => ({
  entity_id: id,
  platform,
  translation_key: key,
});

describe("entity detection", () => {
  it("finds the integration's entities by translation key", () => {
    const found = discoverEntities({
      entities: {
        "select.mode_jour": registry("select.mode_jour", "day_mode"),
        "sensor.other": registry("sensor.other", "next_mode", "other"),
      },
    });
    expect(found.day_mode_entity).toBe("select.mode_jour");
    expect(found.next_mode_entity).toBeUndefined();
  });

  it("is empty without a registry", () => {
    expect(discoverEntities({})).toEqual({});
  });

  it("follows a renamed entity when the configuration leaves it out", async () => {
    const states = homeshiftStates();
    const day = states["select.homeshift_day_mode"];
    states["select.mode_jour"] = entity("select.mode_jour", "Maison", day.attributes);
    delete states["select.homeshift_day_mode"];
    const hass = {
      ...makeHass(states),
      entities: { "select.mode_jour": registry("select.mode_jour", "day_mode") },
    };
    const card = await renderCard(hass);
    await card.updateComplete;
    expect((card as any)._config.day_mode_entity).toBe("select.mode_jour");
  });

  it("keeps an entity written in the configuration", async () => {
    const hass = {
      ...makeHass(homeshiftStates()),
      entities: { "select.mode_jour": registry("select.mode_jour", "day_mode") },
    };
    const card = await renderCard(hass, { day_mode_entity: "select.homeshift_day_mode" });
    expect((card as any)._config.day_mode_entity).toBe("select.homeshift_day_mode");
  });

  it("falls back to the default ids", async () => {
    const card = await renderCard(makeHass(homeshiftStates()));
    expect((card as any)._config.day_mode_entity).toBe("select.homeshift_day_mode");
  });
});
