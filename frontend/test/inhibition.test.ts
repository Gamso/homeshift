import { afterEach, describe, expect, it } from "vitest";
import { $, $$, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

afterEach(() => {
  document.body.innerHTML = "";
});

const IN_THREE_DAYS = new Date(Date.now() + 3 * 86400e3).toISOString();

function withInhibitions(covers: Record<string, string | null> = {}) {
  const states = homeshiftStates();
  states["sensor.homeshift_covers_inhibited"] = entity(
    "sensor.homeshift_covers_inhibited",
    String(Object.keys(covers).length),
    { covers, managed_covers: ["cover.living", "cover.bedroom"] },
  );
  states["cover.living"] = entity("cover.living", "open", { friendly_name: "Living" });
  states["cover.bedroom"] = entity("cover.bedroom", "closed", { friendly_name: "Bedroom" });
  return states;
}

async function openPanel(card: any) {
  const head = $$(card, ".setting-head").find((el) =>
    el.textContent?.includes("Cover automation"),
  )!;
  head.click();
  await card.updateComplete;
}

describe("cover automation pause", () => {
  it("is hidden without the covers_inhibited sensor", async () => {
    const card = await renderCard(makeHass(homeshiftStates()));
    expect(card.shadowRoot!.textContent).not.toContain("Cover automation");
  });

  it("reads Auto while nothing is paused", async () => {
    const card = await renderCard(makeHass(withInhibitions()));
    const head = $$(card, ".setting-head").find((el) =>
      el.textContent?.includes("Cover automation"),
    )!;
    expect(head.querySelector(".setting-value")!.textContent).toBe("Auto");
    expect($(card, ".chip--paused")).toBeNull();
  });

  it("pauses one cover for the picked duration", async () => {
    const hass = makeHass(withInhibitions());
    const card = await renderCard(hass);
    await openPanel(card);

    // Default is one day; one step up gives two.
    $$(card, ".stepper button")[1].click();
    await card.updateComplete;
    expect($(card, ".stepper-value")!.textContent).toBe("2 d");

    $$(card, ".cover-toggle")[1].click();
    expect(hass.callService).toHaveBeenCalledWith("homeshift", "inhibit_covers", {
      entity_id: ["cover.bedroom"],
      duration: { minutes: 2880 },
    });
  });

  it("pauses until resumed at the last step", async () => {
    const hass = makeHass(withInhibitions());
    const card = await renderCard(hass);
    await openPanel(card);
    for (let i = 0; i < 6; i++) {
      $$(card, ".stepper button")[1].click();
      await card.updateComplete;
    }
    expect($(card, ".stepper-value")!.textContent).toBe("Until resumed");

    $$(card, ".cover-toggle")[0].click();
    expect(hass.callService).toHaveBeenCalledWith("homeshift", "inhibit_covers", {
      entity_id: ["cover.living"],
    });
  });

  it("lists paused covers and resumes them", async () => {
    const hass = makeHass(
      withInhibitions({ "cover.bedroom": IN_THREE_DAYS, "cover.living": null }),
    );
    const card = await renderCard(hass);
    expect($(card, ".chip--paused")!.textContent).toContain("Paused: Bedroom, Living");

    await openPanel(card);
    const statuses = $$(card, ".cover-status").map((el) => el.textContent);
    expect(statuses[0]).toBe("Paused until resumed");
    expect(statuses[1]).toMatch(/^Paused until /);

    $$(card, ".cover-toggle")[1].click();
    expect(hass.callService).toHaveBeenCalledWith("homeshift", "resume_covers", {
      entity_id: ["cover.bedroom"],
    });

    $(card, ".resume-all")!.click();
    expect(hass.callService).toHaveBeenCalledWith("homeshift", "resume_covers", {});
  });

  it("ignores an inhibition already over", async () => {
    const past = new Date(Date.now() - 60000).toISOString();
    const card = await renderCard(makeHass(withInhibitions({ "cover.bedroom": past })));
    expect($(card, ".chip--paused")).toBeNull();
  });

  it("shows a refused call as a notification", async () => {
    const hass = makeHass(withInhibitions());
    hass.callService.mockRejectedValueOnce(new Error("nope"));
    const card = await renderCard(hass);
    const messages: string[] = [];
    card.addEventListener("hass-notification", (ev: any) =>
      messages.push(ev.detail.message),
    );
    await openPanel(card);
    $$(card, ".cover-toggle")[0].click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(messages).toEqual(["Could not pause or resume the cover: nope"]);
  });
});
