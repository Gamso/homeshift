import { afterEach, describe, expect, it } from "vitest";
import { $$, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

const OVERRIDE = "number.homeshift_override_duration";

async function openOverride(hass: any) {
  const card = await renderCard(hass);
  $$(card, "button.setting-head")[0].click();
  await card.updateComplete;
  return card;
}

describe("stepper in flight", () => {
  it("steps from the value it sent, not the stale state", async () => {
    const hass = makeHass(homeshiftStates());
    hass.callService.mockReturnValue(new Promise(() => {}));
    const card = await openOverride(hass);
    $$(card, ".stepper button")[1].click();
    await card.updateComplete;
    expect($$(card, ".stepper-value")[0].textContent).toBe("15 min");
    $$(card, ".stepper button")[1].click();
    await card.updateComplete;
    expect(hass.callService.mock.calls.map((call: any[]) => call[2].value)).toEqual([15, 30]);
    expect($$(card, ".stepper-value")[0].textContent).toBe("30 min");
  });

  it("shows the entity again once its new state arrives", async () => {
    const hass = makeHass(homeshiftStates());
    const card = await openOverride(hass);
    $$(card, ".stepper button")[1].click();
    await card.updateComplete;
    card.hass = {
      ...hass,
      states: { ...hass.states, [OVERRIDE]: entity(OVERRIDE, "60") },
    };
    await card.updateComplete;
    expect($$(card, ".stepper-value")[0].textContent).toBe("1h");
  });

  it("drops the sent value and reports it when the call is refused", async () => {
    const hass = makeHass(homeshiftStates());
    hass.callService.mockRejectedValue(new Error("refused"));
    const card = await openOverride(hass);
    const messages: string[] = [];
    card.addEventListener("hass-notification", (ev: any) => messages.push(ev.detail.message));
    await (card as any)._stepSetting("override", [0, 15, 30], 0, 1);
    await card.updateComplete;
    expect($$(card, ".stepper-value")[0].textContent).toBe("No");
    expect(messages).toEqual(["Could not change the setting: refused"]);
  });
});
