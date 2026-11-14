import { LitElement, html, css, nothing, PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";
import { localize } from "../localize/localize";
import { Schedule } from "./timeline";
import "./schedule-timeline";

/**
 * Content of the card's schedules panel: one tab per day mode, the 24 h
 * timelines of the shown mode, and a pencil that swaps them for the
 * scheduler-card list of that mode, to add and edit its schedules.
 */
export class HomeShiftSchedulePanel extends LitElement {
  @property({ attribute: false }) public hass!: any;
  @property({ attribute: false }) public schedules: Schedule[] = [];
  /** Day modes, in the order of the day mode entity: one tab each. */
  @property({ attribute: false }) public modes: string[] = [];
  /** Current day mode: marked with a dot, and shown whenever it changes. */
  @property() public activeMode = "";
  /** Only the schedules acting on these entities, when there are some. */
  @property({ attribute: false }) public entities: string[] = [];
  /** Day mode whose tab is shown. */
  @state() private _selected?: string;
  /** Whether the scheduler card replaces the timelines. */
  @state() private _editing = false;
  /** Bumped when a scheduler card is built, to render it. */
  @state() private _cardsVersion = 0;
  /** One scheduler card per mode, built once and kept while switching tabs. */
  private _cards = new Map<string, HTMLElement>();
  private _building = new Set<string>();
  private _helpers?: Promise<any>;

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("activeMode") && this.modes.includes(this.activeMode)) {
      this._selected = this.activeMode;
    } else if (!this._selected || !this.modes.includes(this._selected)) {
      this._selected = this.modes[0];
    }
    if (changed.has("entities") && changed.get("entities") !== undefined) {
      this._cards = new Map();
      this._building.clear();
    }
  }

  protected updated(): void {
    const card = this._selected ? this._cards.get(this._selected) : undefined;
    if (card && (card as any).hass !== this.hass) (card as any).hass = this.hass;
  }

  /** scheduler-card configuration of one tab: its tag and entities. */
  private _schedulerConfig(mode: string): Record<string, any> {
    return {
      type: "custom:scheduler-card",
      title: false,
      discover_existing: false,
      show_header_toggle: false,
      time_step: 5,
      sort_by: ["title"],
      display_options: {
        primary_info: ["{name}"],
        secondary_info: [
          `<b>${localize(this.hass, "schedule.next_run")}</b> {relative-time}`,
          `<b>${localize(this.hass, "schedule.days")}</b> {days}`,
          "additional-tasks",
        ],
        icon: "entity",
      },
      tags: [mode],
      ...(this.entities.length ? { include: this.entities } : {}),
    };
  }

  /** Scheduler card of a mode, built on first display. */
  private _card(mode: string): HTMLElement | undefined {
    const card = this._cards.get(mode);
    if (card) return card;
    if (!this._building.has(mode)) {
      this._building.add(mode);
      this._buildCard(mode).finally(() => this._building.delete(mode));
    }
    return undefined;
  }

  private async _buildCard(mode: string): Promise<void> {
    const config = this._schedulerConfig(mode);
    const generation = this._cards;
    this._helpers ??=
      (window as any).loadCardHelpers?.() ?? Promise.resolve(undefined);
    const helpers = await this._helpers;
    let card: HTMLElement;
    if (helpers) {
      card = helpers.createCardElement(config);
    } else {
      await customElements.whenDefined("scheduler-card");
      card = document.createElement("scheduler-card");
      (card as any).setConfig(config);
    }
    // The entities changed while the card was being built.
    if (generation !== this._cards) return;
    // Home Assistant asks for a rebuild once a card that loaded late is defined.
    card.addEventListener("ll-rebuild", (ev) => {
      ev.stopPropagation();
      this._cards.delete(mode);
      this._cardsVersion++;
    });
    (card as any).hass = this.hass;
    this._cards.set(mode, card);
    this._cardsVersion++;
  }

  private _select(mode: string) {
    this._selected = mode;
  }

  /** Arrows move to the previous / next tab (wrapping), Home / End to the first / last. */
  private _onTabKeydown(ev: KeyboardEvent) {
    const count = this.modes.length;
    const index = this.modes.indexOf(this._selected ?? "");
    const target = (
      {
        ArrowRight: (index + 1) % count,
        ArrowLeft: (index - 1 + count) % count,
        Home: 0,
        End: count - 1,
      } as Record<string, number>
    )[ev.key];
    if (target === undefined || !count) return;
    this._select(this.modes[target]);
    ev.preventDefault();
    this.updateComplete.then(() =>
      this.shadowRoot
        ?.querySelector<HTMLElement>('[aria-selected="true"]')
        ?.focus(),
    );
  }

  protected render() {
    if (!this.hass || !this._selected) return nothing;
    const selected = this._selected;
    const editLabel = localize(
      this.hass,
      this._editing ? "schedule.back" : "schedule.edit",
    );
    return html`
      <div class="header">
        <div class="tabs" role="tablist" @keydown=${this._onTabKeydown}>
          ${this.modes.map((mode, index) => {
            const isSelected = mode === selected;
            // Only the selected tab's panel is rendered: only it controls one.
            return html`<button
              id="schedule-tab-${index}"
              class="tab ${isSelected ? "selected" : ""}"
              role="tab"
              aria-selected=${isSelected ? "true" : "false"}
              aria-controls=${isSelected ? "schedule-tabpanel" : nothing}
              tabindex=${isSelected ? 0 : -1}
              @click=${() => this._select(mode)}
            >
              <span class="label">${mode}</span>
              ${mode === this.activeMode
                ? html`<span
                    class="active-dot"
                    role="img"
                    title=${localize(this.hass, "schedule.active_mode")}
                    aria-label=${localize(this.hass, "schedule.active_mode")}
                  ></span>`
                : nothing}
            </button>`;
          })}
        </div>
        <button
          class="edit"
          title=${editLabel}
          aria-label=${editLabel}
          aria-pressed=${this._editing ? "true" : "false"}
          @click=${() => (this._editing = !this._editing)}
        >
          <ha-icon
            icon=${this._editing ? "mdi:chart-timeline" : "mdi:pencil"}
          ></ha-icon>
        </button>
      </div>
      ${this._editing
        ? nothing
        : html`<p class="note ${selected === this.activeMode ? "active" : ""}">
            <ha-icon
              icon=${selected === this.activeMode
                ? "mdi:circle-medium"
                : "mdi:information-outline"}
            ></ha-icon>
            ${localize(
              this.hass,
              selected === this.activeMode
                ? "schedule.note_active"
                : "schedule.note_inactive",
            )}
          </p>`}
      <div
        id="schedule-tabpanel"
        class="content"
        role="tabpanel"
        aria-labelledby="schedule-tab-${this.modes.indexOf(selected)}"
      >
        ${this._editing
          ? (this._card(selected) ?? nothing)
          : html`<homeshift-schedule-timeline
              .hass=${this.hass}
              .schedules=${this.schedules}
              .tag=${selected}
              .entities=${this.entities}
            ></homeshift-schedule-timeline>`}
      </div>
    `;
  }

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    /* Segmented control, as the thermostat modes: the shown mode filled
       with the card's colour (--m, inherited from the card). */
    .tabs {
      flex: 1;
      min-width: 0;
      display: flex;
      gap: 4px;
      padding: 3px;
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.28);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
      overflow-x: auto;
      scrollbar-width: none;
    }
    .tab {
      flex: 1 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      height: 36px;
      padding: 0 10px;
      border: none;
      border-radius: 11px;
      background: none;
      cursor: pointer;
      font: inherit;
      font-size: 12.5px;
      font-weight: 500;
      white-space: nowrap;
      color: var(--secondary-text-color);
      transition:
        background 0.3s,
        color 0.3s,
        box-shadow 0.3s;
    }
    .tab:hover:not(.selected) {
      background: rgba(255, 255, 255, 0.06);
      color: var(--primary-text-color);
    }
    .tab:focus-visible,
    .edit:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }
    .tab.selected {
      color: #fff;
      background: linear-gradient(
        180deg,
        rgba(var(--m, 3, 169, 244), 0.95),
        rgba(var(--m, 3, 169, 244), 0.7)
      );
      box-shadow: 0 3px 12px -2px rgba(var(--m, 3, 169, 244), 0.6);
    }
    .active-dot {
      flex: none;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #ffd24d;
      box-shadow: 0 0 6px #ffd24d;
    }
    .edit {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      padding: 0;
      border: none;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
      color: rgb(var(--m, 3, 169, 244));
      cursor: pointer;
      --mdc-icon-size: 18px;
    }
    .edit:hover {
      background: rgba(255, 255, 255, 0.12);
    }
    .edit[aria-pressed="true"] {
      background: rgba(var(--m, 3, 169, 244), 0.85);
      color: #fff;
    }
    /* Whether the shown mode is the one whose schedules run. */
    .note {
      display: flex;
      align-items: center;
      gap: 6px;
      margin: -4px 0 0;
      font-size: 11.5px;
      color: var(--secondary-text-color);
      --mdc-icon-size: 15px;
    }
    .note.active ha-icon {
      color: #ffd24d;
    }
    /* The scheduler card blends into the panel. */
    .content {
      --ha-card-border-width: 0;
      --ha-card-box-shadow: none;
      --ha-card-background: transparent;
    }
  `;
}

if (!customElements.get("homeshift-schedule-panel")) {
  customElements.define("homeshift-schedule-panel", HomeShiftSchedulePanel);
}
