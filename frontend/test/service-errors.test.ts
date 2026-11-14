import { afterEach, describe, expect, it } from "vitest";
import { $, $$, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

/** A card whose service calls are refused, and the toasts it raises. */
async function refusingCard() {
  const hass = makeHass(homeshiftStates());
  hass.callService.mockRejectedValue(new Error("refused"));
  const card = await renderCard(hass);
  const messages: string[] = [];
  card.addEventListener("hass-notification", (ev: any) =>
    messages.push(ev.detail.message),
  );
  return { card, messages };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe("refused service calls", () => {
  it("reports a refused thermostat mode", async () => {
    const { card, messages } = await refusingCard();
    $$(card, "button.preset")[2].click();
    await flush();
    expect(messages).toEqual(["Could not change the mode: refused"]);
  });

  it("reports a refused day mode", async () => {
    const { card, messages } = await refusingCard();
    $(card, ".day-mode-button")!.click();
    await card.updateComplete;
    $$(card, ".day-mode-option")[0].click();
    await flush();
    expect(messages).toEqual(["Could not change the mode: refused"]);
  });

  it("reports a refused setting", async () => {
    const { card, messages } = await refusingCard();
    $$(card, "button.setting-head")[0].click();
    await card.updateComplete;
    $$(card, ".stepper button")[1].click();
    await flush();
    expect(messages).toEqual(["Could not change the setting: refused"]);
  });
});
