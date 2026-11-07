import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { localize } from "../src/localize/localize";
import en from "../src/localize/en.json";
import fr from "../src/localize/fr.json";

const FR = { locale: { language: "fr" } };

function leafKeys(obj: Record<string, any>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" ? leafKeys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe("localize", () => {
  it("resolves a key in the user's language", () => {
    expect(localize(FR, "thermostat.off")).toBe("Éteint");
  });

  it("falls back to English for an unknown language", () => {
    expect(localize({ locale: { language: "de" } }, "thermostat.off")).toBe("Off");
  });

  it("uses the region-less language code", () => {
    expect(localize({ locale: { language: "fr-CA" } }, "thermostat.off")).toBe(
      "Éteint",
    );
  });

  it("returns the caller's fallback for a missing key", () => {
    expect(localize(FR, "thermostat.dehumidify", undefined, "Déshu")).toBe(
      "Déshu",
    );
  });

  it("returns the key when nothing else is available", () => {
    expect(localize(FR, "card.does_not_exist")).toBe("card.does_not_exist");
  });

  it("substitutes parameters", () => {
    expect(localize(FR, "card.covers_left_open", { covers: "Salon" })).toBe(
      "Non fermés : Salon",
    );
  });

  it("has the same keys in every language", () => {
    expect(leafKeys(fr).sort()).toEqual(leafKeys(en).sort());
  });

  it("has no key the sources never use", () => {
    // Vitest runs from the repository root.
    const source = ["src/components", "src/schedule"]
      .map((sub) => join(process.cwd(), sub))
      .flatMap((dir) =>
        readdirSync(dir).map((f) => readFileSync(join(dir, f), "utf-8")),
      )
      .join("\n");
    // Keys built at runtime: `thermostat.${key}`, `preview.${key}`,
    // `editor.${field.key}`, `card.cover_${action}_...` and
    // `schedule.${value.kind}`.
    const dynamic = [
      /^thermostat\./,
      /^preview\./,
      /^editor\./,
      /^card\.cover_(open|close)_(time|action|failed)$/,
      /^schedule\.(on|off)$/,
    ];
    const unused = leafKeys(en).filter(
      (key) =>
        !source.includes(`"${key}"`) && !dynamic.some((re) => re.test(key)),
    );
    expect(unused).toEqual([]);
  });
});
