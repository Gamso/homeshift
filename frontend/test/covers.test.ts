import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { HomeShiftCard } from "../src/components/homeshift-card";
import { $, $$, entity, homeshiftStates, makeHass, renderCard } from "./helpers";

beforeAll(() => {
  HomeShiftCard.COVER_FEEDBACK_MS = 0;
});

afterEach(() => {
  document.body.innerHTML = "";
});

function withButtons(state = "unknown") {
  const states = homeshiftStates();
  for (const id of ["button.homeshift_open_covers", "button.homeshift_close_covers"]) {
    states[id] = entity(id, state);
  }
  return states;
}

describe("manual cover open / close", () => {
  it("renders labelled buttons that press the integration buttons", async () => {
    const hass = makeHass(withButtons());
    const card = await renderCard(hass);
    const [open, close] = $$(card, "button.cover-time");
    expect(open.getAttribute("aria-label")).toBe(
      "Open the covers now (scheduled 08:30)",
    );
    expect(close.getAttribute("aria-label")).toBe(
      "Close the covers now (scheduled 21:15)",
    );

    close.click();
    expect(hass.callService).toHaveBeenCalledWith("button", "press", {
      entity_id: "button.homeshift_close_covers",
    });
  });

  it("uses the French labels", async () => {
    const card = await renderCard(makeHass(withButtons(), "fr"));
    expect($(card, "button.cover-time")?.getAttribute("aria-label")).toBe(
      "Ouvrir les volets maintenant (prévu à 08:30)",
    );
  });

  it("presses configured button entities", async () => {
    const states = withButtons();
    states["button.my_open"] = entity("button.my_open", "2026-01-01T08:00:00+00:00");
    const hass = makeHass(states);
    const card = await renderCard(hass, { open_covers_entity: "button.my_open" });
    $(card, "button.cover-time")!.click();
    expect(hass.callService).toHaveBeenCalledWith("button", "press", {
      entity_id: "button.my_open",
    });
  });

  it.each([
    ["missing", undefined],
    ["unavailable", "unavailable"],
  ])("keeps plain labels when the buttons are %s", async (_name, state) => {
    const states = state ? withButtons(state) : homeshiftStates();
    const hass = makeHass(states);
    const card = await renderCard(hass);
    expect($$(card, "button.cover-time")).toHaveLength(0);
    $(card, ".cover-time")!.click();
    expect(hass.callService).not.toHaveBeenCalled();
  });

  it("gives the legacy cover_entity priority over the buttons", async () => {
    const states = withButtons();
    states["cover.living"] = entity("cover.living", "closed");
    const hass = makeHass(states);
    const card = await renderCard(hass, { cover_entity: "cover.living" });
    $(card, "button.cover-time")!.click();
    expect(hass.callService).toHaveBeenCalledWith("cover", "open_cover", {
      entity_id: "cover.living",
    });
  });

  it("shows a sending state while the call is in flight", async () => {
    const hass = makeHass(withButtons());
    let resolve!: () => void;
    hass.callService.mockReturnValue(new Promise<void>((r) => (resolve = r)));
    const card = await renderCard(hass);
    $(card, "button.cover-time")!.click();
    await card.updateComplete;
    const [open, close] = $$(card, "button.cover-time") as HTMLButtonElement[];
    expect(open.classList.contains("pending")).toBe(true);
    expect(open.getAttribute("aria-busy")).toBe("true");
    expect(open.textContent).toContain("Sending");
    expect(close.disabled).toBe(true);

    resolve();
    await vi.waitFor(() =>
      expect($(card, "button.cover-time")!.classList.contains("pending")).toBe(false),
    );
  });

  it("reports a failed call through hass-notification", async () => {
    const hass = makeHass(withButtons());
    hass.callService.mockRejectedValue(new Error("Entity is unavailable"));
    const card = await renderCard(hass);
    const toast = vi.fn();
    card.addEventListener("hass-notification", (e) =>
      toast((e as CustomEvent).detail.message),
    );
    $(card, "button.cover-time")!.click();
    await vi.waitFor(() =>
      expect(toast).toHaveBeenCalledWith(
        "Could not open the covers: Entity is unavailable",
      ),
    );
    expect($(card, "button.cover-time")!.classList.contains("pending")).toBe(false);
  });
});
