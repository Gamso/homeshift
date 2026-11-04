import { afterEach, describe, expect, it } from "vitest";
import { HomeShiftCard } from "../src/components/homeshift-card";
import { HomeShiftCardEditor } from "../src/components/homeshift-card-editor";
import en from "../src/localize/en.json";
import fr from "../src/localize/fr.json";

const hass = { states: {}, locale: { language: "en" } };

async function renderEditor(
  config: Record<string, unknown> = {},
): Promise<HomeShiftCardEditor> {
  const editor = document.createElement(
    "homeshift-card-editor",
  ) as HomeShiftCardEditor;
  (editor as any).hass = hass;
  editor.setConfig({ ...HomeShiftCard.getStubConfig(), ...config });
  document.body.appendChild(editor);
  await editor.updateComplete;
  return editor;
}

function cardConfigKeys(): string[] {
  const card = new HomeShiftCard();
  card.setConfig({});
  return Object.keys((card as any)._config);
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("homeshift-card-editor", () => {
  it("only writes keys the card reads", async () => {
    const editor = await renderEditor();
    const written = new Set<string>();
    editor.addEventListener("config-changed", (e: Event) => {
      const config = (e as CustomEvent).detail.config;
      Object.keys(config).forEach((k) => written.add(k));
    });

    const pickers = editor.shadowRoot!.querySelectorAll("ha-entity-picker");
    pickers.forEach((picker, i) =>
      picker.dispatchEvent(
        new CustomEvent("value-changed", { detail: { value: `sensor.x${i}` } }),
      ),
    );

    expect(written.size).toBeGreaterThan(0);
    const cardKeys = cardConfigKeys();
    for (const key of written) expect(cardKeys).toContain(key);
  });

  it("leaves the entities to the detection in a new card", () => {
    expect(HomeShiftCard.getStubConfig()).toEqual({ name: "Thermostat" });
  });

  it("exposes every entity option of the card", async () => {
    const editor = await renderEditor();
    const pickers = editor.shadowRoot!.querySelectorAll("ha-entity-picker");
    const entityKeys = cardConfigKeys().filter((k) => k.endsWith("_entity"));
    expect(pickers.length).toBe(entityKeys.length);
  });

  it("shows the thermostat entity of an existing YAML config", async () => {
    const editor = await renderEditor({
      thermostat_mode_entity: "select.homeshift_thermostat_mode",
    });
    const values = [
      ...editor.shadowRoot!.querySelectorAll("ha-entity-picker"),
    ].map((p) => (p as any).value);
    expect(values).toContain("select.homeshift_thermostat_mode");
  });

  it("has a label in every language for every option", () => {
    for (const dict of [en, fr]) {
      for (const key of cardConfigKeys()) {
        expect(dict.editor, key).toHaveProperty(key);
      }
    }
  });

  it("has no label for an option the card does not have", () => {
    for (const dict of [en, fr]) {
      const options = Object.keys(dict.editor).filter(
        (k) => !["entities", "entities_hint"].includes(k),
      );
      expect(options.sort()).toEqual(cardConfigKeys().sort());
    }
  });
});
