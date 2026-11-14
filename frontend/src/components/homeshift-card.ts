import { LitElement, html, svg, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import { localize } from "../localize/localize";
import "./homeshift-card-editor";
import { cardStyles } from "./homeshift-card.styles";
import { ENTITY_FIELDS, HomeShiftCardConfig } from "../types";
import { discoverEntities } from "../entities";
import { formatMinutes, isUsable, numericState } from "../state";
import { formatShortDate, formatTime } from "../time";
import { callService, notifyFailure } from "../notify";
import "../schedule/schedule-panel";
import { Schedule } from "../schedule/timeline";

type CoverAction = "open" | "close";
type SettingName = "override" | "early" | "covers";

/** One climate of HomeShift's auto_start_stop sensor. */
interface HeatPump {
  switch: string;
  name: string;
  /** Whether HomeShift drives it in the current thermostat mode. */
  driven: boolean;
  /** On the comfort side of its threshold (auto start/stop off, the climate runs); null when not driven. */
  comfort: boolean | null;
  /** The switch's actual state, null when unavailable. */
  auto_start_stop: boolean | null;
  /** The switch differs from what HomeShift set: flipped by hand. */
  manual: boolean;
  /** The climate's target temperature and the threshold of the thermostat mode (°). */
  setpoint?: number | null;
  threshold?: number | null;
  /** Which side of the threshold keeps the climate running. */
  comfort_when?: "above" | "below" | null;
}

/** Covers HomeShift drives, and the end of each running inhibition (null: until resumed). */
interface CoverInhibitions {
  managed: string[];
  inhibited: Map<string, string | null>;
}

/** Colour ("r, g, b") and icon of each thermostat mode; anything else is neutral. */
const MODE_STYLES: Record<string, { rgb: string; icon: string }> = {
  off: { rgb: "148, 163, 184", icon: "mdi:power" },
  heating: { rgb: "255, 122, 42", icon: "mdi:fire" },
  cooling: { rgb: "56, 160, 240", icon: "mdi:snowflake" },
  ventilation: { rgb: "45, 212, 160", icon: "mdi:fan" },
};
const NEUTRAL_MODE = { rgb: "148, 163, 184", icon: "mdi:thermostat" };

/** Icon of a day mode, from its key; a mode added by the user gets a calendar. */
const DAY_ICONS: Record<string, string> = {
  home: "mdi:home",
  work: "mdi:briefcase",
  remote: "mdi:laptop",
  away: "mdi:airplane",
};

/**
 * Embers, snowflakes or air streaks behind the card, one per entry: left
 * edge and height in %, duration and delay in s, drift in px. Fixed rather
 * than random so a render does not move them.
 */
const PARTICLES = [
  [6, 4.2, 0.0, -8, 30],
  [17, 5.1, 1.6, 12, 72],
  [28, 3.6, 3.1, -14, 48],
  [39, 4.8, 0.7, 6, 86],
  [50, 3.9, 2.4, -4, 22],
  [61, 5.4, 3.6, 16, 58],
  [72, 4.4, 1.1, -10, 40],
  [83, 3.7, 2.9, 8, 78],
  [91, 5.0, 0.4, -16, 64],
  [45, 4.6, 3.9, 10, 92],
];

/** Roller shutter, up with an arrow (open) or down (close). */
const coverIcon = (action: CoverAction) => svg`<svg
  class="cover-icon"
  viewBox="0 0 24 24"
  aria-hidden="true"
>
  <rect class="solid" x="3" y="3" width="18" height="4" rx="1.5" />
  <path class="rails" d="M5 7v14M19 7v14" />
  ${action === "open"
    ? svg`<path class="fill" d="M5 7h14v6H5z" />
        <path d="M5 10h14M5 13h14" />
        <path d="M12 20v-4M9.8 18.2 12 16l2.2 2.2" />`
    : svg`<path class="fill" d="M5 7h14v14H5z" />
        <path d="M5 10h14M5 13h14M5 16h14M5 19h14" />`}
</svg>`;

class HomeShiftCard extends LitElement {
  /** Minimum time the "sending" state of a cover button stays visible. */
  static COVER_FEEDBACK_MS = 600;

  // Override duration steps in minutes (0 = disabled).
  private static readonly OVERRIDE_PRESETS = [0, 15, 30, 60, 120, 240, 480, 720];

  // Early-switch anticipation steps in minutes (0 = disabled).
  private static readonly EARLY_SWITCH_PRESETS = [
    0, 15, 30, 45, 60, 90, 120, 180, 240,
  ];

  // How long a cover is paused for, in minutes (0 = until resumed).
  private static readonly INHIBIT_PRESETS = [240, 1440, 2880, 4320, 10080, 0];
  private static readonly INHIBIT_DEFAULT_INDEX = 1;

  @property({ attribute: false }) public hass!: any;
  /** Set by Home Assistant in the card picker and the editor preview. */
  @property({ type: Boolean }) public preview = false;
  @state() private _config!: HomeShiftCardConfig;
  /** The configuration as written: what is not in it is detected. */
  private _written: HomeShiftCardConfig = {};
  @state() private _openSetting: SettingName | null = null;
  /** Index in INHIBIT_PRESETS of the pause duration picked in the covers row. */
  @state() private _inhibitIndex = HomeShiftCard.INHIBIT_DEFAULT_INDEX;
  /** Cover button whose service call is in flight. */
  @state() private _coverPending?: CoverAction;
  /** Whether the full list behind a "Not closed: N covers" chip is shown. */
  @state() private _coversExpanded = false;
  /** Bumped at midnight so the "Today" / "Tomorrow" prefixes roll over. */
  @state() private _day = 0;
  /** Every schedule of the Scheduler integration, once read (schedules panel). */
  @state() private _schedules?: Schedule[];
  /** Whether the schedules panel covers the card. */
  @state() private _schedulesOpen = false;
  /** Whether the day mode list is open, and the option the keyboard is on. */
  @state() private _dayOpen = false;
  @state() private _dayActive = 0;
  /** Whether the climate section is unfolded. */
  @state() private _heatPumpsOpen = false;
  /** Fingerprint of the schedule switches, to read the schedules again when they change. */
  private _schedulesKey?: string;
  private _midnightTimer?: ReturnType<typeof setTimeout>;
  private _settingTimeout?: ReturnType<typeof setTimeout>;

  connectedCallback() {
    super.connectedCallback();
    this._scheduleMidnightRefresh();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._midnightTimer);
    clearTimeout(this._settingTimeout);
  }

  /**
   * Entity changes already trigger renders, and so does opening a setting
   * (its "until {time}" text is computed then); the only output that goes
   * stale on its own is the day prefix of the next-mode time, at midnight.
   */
  private _scheduleMidnightRefresh() {
    clearTimeout(this._midnightTimer);
    const now = new Date();
    const nextMidnight = new Date(now);
    nextMidnight.setHours(24, 0, 1, 0);
    this._midnightTimer = setTimeout(() => {
      this._day++;
      this._scheduleMidnightRefresh();
    }, nextMidnight.getTime() - now.getTime());
  }

  public static getStubConfig(): HomeShiftCardConfig {
    return { name: "Thermostat" };
  }

  public static getConfigElement() {
    return document.createElement("homeshift-card-editor");
  }

  public setConfig(config: HomeShiftCardConfig): void {
    if (!config) {
      throw new Error("Missing configuration");
    }
    this._written = config;
    const normalized: HomeShiftCardConfig = {
      name: config.name ?? "Thermostat",
    };
    for (const field of ENTITY_FIELDS) {
      normalized[field.key] = config[field.key] ?? field.default;
    }
    normalized.show_schedules = config.show_schedules !== false;
    normalized.schedule_entities = Array.isArray(config.schedule_entities)
      ? config.schedule_entities
      : [];
    this._config = normalized;
  }

  /**
   * Point the entity options that the configuration leaves out at the
   * entities the integration registered. Returns true when one moved.
   */
  private _detectEntities(): boolean {
    if (!this._config || !this.hass) return false;
    const found = discoverEntities(this.hass);
    const next = { ...this._config };
    let moved = false;
    for (const field of ENTITY_FIELDS) {
      const wanted = this._written[field.key] ?? found[field.key] ?? field.default;
      if (next[field.key] !== wanted) {
        next[field.key] = wanted;
        moved = true;
      }
    }
    if (moved) this._config = next;
    return moved;
  }

  public getCardSize(): number {
    return 4;
  }

  protected shouldUpdate(changedProps: Map<string, unknown>): boolean {
    // Here rather than in willUpdate: most hass updates stop at this method.
    if (changedProps.has("hass")) {
      this._refreshSchedules();
      if (this._detectEntities()) return true;
    }
    if (changedProps.has("_config") || changedProps.has("preview")) return true;
    if (
      changedProps.has("_day") ||
      changedProps.has("_openSetting") ||
      changedProps.has("_inhibitIndex") ||
      changedProps.has("_coversExpanded") ||
      changedProps.has("_coverPending") ||
      changedProps.has("_schedules") ||
      changedProps.has("_schedulesOpen") ||
      changedProps.has("_dayOpen") ||
      changedProps.has("_heatPumpsOpen") ||
      changedProps.has("_dayActive")
    )
      return true;
    if (changedProps.has("hass")) {
      const oldHass = changedProps.get("hass") as any;
      if (!oldHass) return true;
      // The open panel shows the schedule switches and the room temperatures.
      if (this._schedulesOpen) return true;
      const watchedEntities = ENTITY_FIELDS.map(
        (field) => this._config?.[field.key],
      ).filter(Boolean) as string[];
      return watchedEntities.some(
        (id) => oldHass.states[id] !== this.hass.states[id],
      );
    }
    return false;
  }

  /** Colour class for a preset: its key, or the display name it was given.

   * A select exposing option_map hands over stable keys (off, heating, …).
   * Without it, the only thing left is the display value, which is the
   * user's own wording — so known labels are mapped back to a key, and
   * anything else falls through to the neutral colour rather than breaking
   * the class name.
   */
  private _presetClass(key: string, display: string): string {
    const slug = (text: string) =>
      text
        .toLowerCase()
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .replace(/[^a-z0-9]+/g, "-");
    const known = ["off", "heating", "cooling", "ventilation"];
    if (known.includes(slug(key))) return slug(key);
    const byLabel: Record<string, string> = {
      eteint: "off",
      arret: "off",
      off: "off",
      chauffage: "heating",
      heat: "heating",
      heating: "heating",
      climatisation: "cooling",
      clim: "cooling",
      cool: "cooling",
      cooling: "cooling",
      ventilation: "ventilation",
      ventilateur: "ventilation",
      fan: "ventilation",
    };
    return byLabel[slug(display)] ?? slug(key);
  }

  private getEntityState(entityId?: string) {
    if (!entityId) return undefined;
    return this.hass?.states?.[entityId];
  }

  /** The covers tonight's close had to leave up, by friendly name. */
  private getCoversLeftOpen(): string[] {
    const covers = this.getEntityState(this._config?.covers_left_open_entity)
      ?.attributes?.covers;
    if (!Array.isArray(covers)) return [];
    return covers.map(
      (id: string) =>
        this.hass?.states?.[id]?.attributes?.friendly_name ?? id,
    );
  }

  private _friendlyName(entityId: string): string {
    return this.hass?.states?.[entityId]?.attributes?.friendly_name ?? entityId;
  }

  /**
   * Every cover HomeShift drives, and the running inhibitions. An end
   * already past is dropped here rather than waiting for the integration's
   * next poll to forget it.
   */
  private getCoverInhibitions(): CoverInhibitions {
    const attributes =
      this.getEntityState(this._config?.covers_inhibited_entity)?.attributes ??
      {};
    const managed: string[] = Array.isArray(attributes.managed_covers)
      ? attributes.managed_covers
      : [];
    const inhibited = new Map<string, string | null>();
    const now = Date.now();
    for (const [cover, until] of Object.entries(attributes.covers ?? {})) {
      if (typeof until === "string" && new Date(until).getTime() <= now) {
        continue;
      }
      inhibited.set(cover, typeof until === "string" ? until : null);
    }
    return { managed, inhibited };
  }

  /** The climates of the auto_start_stop sensor, [] without it. */
  private getHeatPumps(): HeatPump[] {
    const pumps = this.getEntityState(this._config?.auto_start_stop_entity)
      ?.attributes?.climates;
    return Array.isArray(pumps) ? pumps : [];
  }

  /** Flip a climate's auto start/stop by hand; HomeShift takes over at the next change. */
  private async _toggleHeatPump(pump: HeatPump) {
    await callService(this, this.hass, "card.heat_pump_failed", "switch", "toggle", {
      entity_id: pump.switch,
    });
  }

  /**
   * Folded state of the climate section: each state with its count
   * ("1 Comfort · 2 Auto"), or just the state when there is one climate.
   */
  private _heatPumpsSummary(pumps: HeatPump[]): string {
    const labels: [string, (pump: HeatPump) => boolean][] = [
      [localize(this.hass, "card.heat_pump_comfort"), (p) => p.driven && !!p.comfort],
      [localize(this.hass, "card.heat_pump_auto"), (p) => p.driven && !p.comfort],
      [localize(this.hass, "card.heat_pump_not_driven_short"), (p) => !p.driven],
    ];
    const parts = labels
      .map(([label, test]) => [label, pumps.filter(test).length] as const)
      .filter(([, count]) => count > 0);
    if (pumps.length === 1) return parts[0]?.[0] ?? "";
    return parts.map(([label, count]) => `${count} ${label}`).join(" · ");
  }

  /**
   * Foldable section, one row per climate: Auto (VTherm may stop it),
   * Comfort (it runs), or not driven in this thermostat mode. A tap on a
   * row flips it by hand.
   */
  private _renderHeatPumps(pumps: HeatPump[], thermostatOff: boolean) {
    const open = this._heatPumpsOpen;
    const manual = pumps.some((pump) => pump.manual);
    return html`<div class="heat-pumps ${open ? "open" : ""}">
      <button
        type="button"
        class="heat-pumps-head"
        aria-expanded=${open ? "true" : "false"}
        aria-controls="heat-pump-list"
        @click=${() => (this._heatPumpsOpen = !open)}
      >
        <ha-icon icon="mdi:hvac"></ha-icon>
        <span class="heat-pumps-title">${localize(this.hass, "card.heat_pumps")}</span>
        <span class="heat-pumps-summary">${this._heatPumpsSummary(pumps)}</span>
        ${manual
          ? html`<ha-icon
              class="manual"
              icon="mdi:hand-back-left"
              title=${localize(this.hass, "card.heat_pump_manual")}
              aria-label=${localize(this.hass, "card.heat_pump_manual")}
              role="img"
            ></ha-icon>`
          : nothing}
        <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
      </button>
      ${open
        ? html`<div id="heat-pump-list" class="heat-pump-list">
            ${pumps.map((pump) => {
        const state = !pump.driven ? "idle" : pump.comfort ? "comfort" : "auto";
        let text: string;
        if (!pump.driven) {
          text = localize(
            this.hass,
            thermostatOff ? "card.heat_pump_thermostat_off" : "card.heat_pump_not_driven",
          );
        } else {
          const below = pump.comfort_when === "below";
          const key = pump.comfort
            ? below
              ? "card.heat_pump_runs_up_to"
              : "card.heat_pump_runs_from"
            : below
              ? "card.heat_pump_stops_above"
              : "card.heat_pump_stops_below";
          text = localize(this.hass, key, {
            setpoint: String(pump.setpoint ?? "—"),
            threshold: String(pump.threshold ?? "—"),
          });
        }
        const tag = localize(
          this.hass,
          {
            idle: "card.heat_pump_idle",
            comfort: "card.heat_pump_comfort",
            auto: "card.heat_pump_auto",
          }[state],
        );
        return html`<button
          type="button"
          class="heat-pump ${state}"
          aria-label="${pump.name} — ${tag}. ${text}"
          ?disabled=${!pump.driven || pump.auto_start_stop === null}
          @click=${() => this._toggleHeatPump(pump)}
        >
          <span class="heat-pump-icon">
            <ha-icon icon=${state === "auto" ? "mdi:leaf" : "mdi:hvac"}></ha-icon>
          </span>
          <span class="heat-pump-text">
            <span class="heat-pump-name">${pump.name}</span>
            <span class="heat-pump-status"
              >${pump.manual
                ? html`<span class="heat-pump-manual"
                      >${localize(this.hass, "card.heat_pump_manual")}</span
                    >
                    · `
                : nothing}${text}</span
            >
          </span>
          <span class="heat-pump-tag">
            ${state === "idle"
              ? nothing
              : html`<ha-icon icon=${state === "auto" ? "mdi:leaf" : "mdi:fire"}></ha-icon>`}
            ${tag}
          </span>
        </button>`;
            })}
          </div>`
        : nothing}
    </div>`;
  }

  /** Call a HomeShift cover service; show a refusal as Home Assistant's toast. */
  private async _callInhibitService(service: string, data: Record<string, unknown>) {
    this._armSettingTimeout();
    await callService(this, this.hass, "card.inhibit_failed", "homeshift", service, data);
  }

  private _inhibitCover(entityId: string) {
    const minutes = HomeShiftCard.INHIBIT_PRESETS[this._inhibitIndex];
    this._callInhibitService("inhibit_covers", {
      entity_id: [entityId],
      ...(minutes ? { duration: { minutes } } : {}),
    });
  }

  private _resumeCovers(entityIds?: string[]) {
    this._callInhibitService(
      "resume_covers",
      entityIds ? { entity_id: entityIds } : {},
    );
  }

  private _stepInhibit(direction: 1 | -1) {
    const last = HomeShiftCard.INHIBIT_PRESETS.length - 1;
    this._inhibitIndex = Math.min(
      last,
      Math.max(0, this._inhibitIndex + direction),
    );
    this._armSettingTimeout();
  }

  /** "4h", "3 d" / "3 j", or "Until resumed". */
  private _inhibitLabel(minutes: number): string {
    if (!minutes) return localize(this.hass, "card.inhibit_forever");
    if (minutes < 1440) return formatMinutes(minutes);
    return `${minutes / 1440} ${localize(this.hass, "card.days_short")}`;
  }

  private _inhibitEnd(until: string | null): string {
    return until
      ? localize(this.hass, "card.inhibited_until", {
          time: this._formatAbsoluteTime(until),
        })
      : localize(this.hass, "card.inhibited_forever");
  }

  /** Collapsible row pausing the automation of chosen covers. */
  private _renderCoverInhibition({ managed, inhibited }: CoverInhibitions) {
    const open = this._openSetting === "covers";
    const presets = HomeShiftCard.INHIBIT_PRESETS;
    const minutes = presets[this._inhibitIndex];
    const label = localize(this.hass, "card.inhibit_label");
    const effect = minutes
      ? localize(this.hass, "card.inhibit_effect", {
          duration: this._inhibitLabel(minutes),
          time: this._formatAbsoluteTime(
            new Date(Date.now() + minutes * 60000).toISOString(),
          ),
        })
      : localize(this.hass, "card.inhibit_effect_forever");
    return html`<div class="setting ${open ? "open" : ""}">
      <button
        class="setting-head"
        aria-expanded=${open ? "true" : "false"}
        @click=${() => this._toggleSetting("covers")}
      >
        <ha-icon icon="mdi:window-shutter-cog"></ha-icon>
        <span class="setting-label">${label}</span>
        <span class="setting-value ${inhibited.size ? "set" : ""}"
          >${inhibited.size
            ? localize(this.hass, "card.inhibited_count", {
                count: String(inhibited.size),
              })
            : localize(this.hass, "card.inhibit_none")}</span
        >
        <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
      </button>
      ${open
        ? html`<div class="setting-body">
            <div class="stepper">
              <button
                aria-label=${localize(this.hass, "card.decrease", {
                  setting: label,
                })}
                ?disabled=${this._inhibitIndex <= 0}
                @click=${() => this._stepInhibit(-1)}
              >
                −
              </button>
              <span class="stepper-value" aria-live="polite"
                >${this._inhibitLabel(minutes)}</span
              >
              <button
                aria-label=${localize(this.hass, "card.increase", {
                  setting: label,
                })}
                ?disabled=${this._inhibitIndex >= presets.length - 1}
                @click=${() => this._stepInhibit(1)}
              >
                +
              </button>
            </div>
            <p class="setting-effect">${effect}</p>
            <ul class="cover-list">
              ${managed.map((cover) => {
                const paused = inhibited.has(cover);
                const name = this._friendlyName(cover);
                const action = localize(
                  this.hass,
                  paused ? "card.resume" : "card.pause",
                );
                return html`<li class="cover-item ${paused ? "paused" : ""}">
                  <span class="cover-name">
                    ${name}
                    <span class="cover-status"
                      >${paused
                        ? this._inhibitEnd(inhibited.get(cover) ?? null)
                        : localize(this.hass, "card.inhibit_none")}</span
                    >
                  </span>
                  <button
                    type="button"
                    class="cover-toggle"
                    aria-label="${action} — ${name}"
                    @click=${() =>
                      paused
                        ? this._resumeCovers([cover])
                        : this._inhibitCover(cover)}
                  >
                    <ha-icon icon=${paused ? "mdi:play" : "mdi:pause"}></ha-icon>
                    ${action}
                  </button>
                </li>`;
              })}
            </ul>
            ${inhibited.size > 1
              ? html`<button
                  type="button"
                  class="resume-all"
                  @click=${() => this._resumeCovers()}
                >
                  ${localize(this.hass, "card.resume_all")}
                </button>`
              : nothing}
          </div>`
        : nothing}
    </div>`;
  }

  /**
   * Reads the schedules again when a schedule switch changes: the Scheduler
   * integration updates them whenever a schedule is edited, toggled or run.
   * Without the integration the call fails and the panel stays hidden.
   */
  private _refreshSchedules() {
    if (!this._config?.show_schedules || this.preview || !this.hass?.callWS) {
      return;
    }
    const key = Object.values(this.hass.states ?? {})
      .filter((s: any) => s.entity_id.startsWith("switch.schedule"))
      .map((s: any) => `${s.entity_id}:${s.last_updated}`)
      .join("|");
    if (key === this._schedulesKey) return;
    this._schedulesKey = key;
    this.hass
      .callWS({ type: "scheduler" })
      .then((schedules: Schedule[]) => {
        this._schedules = Array.isArray(schedules) ? schedules : undefined;
      })
      .catch(() => {
        this._schedules = undefined;
      });
  }

  /** Whether a schedule is tagged with one of the day modes. */
  private _hasDaySchedules(dayModes: string[]): boolean {
    return (this._schedules ?? []).some((schedule) =>
      schedule.tags?.some((tag) => dayModes.includes(tag)),
    );
  }

  private _toggleSchedules(open: boolean) {
    this._schedulesOpen = open;
    // Keep the focus on the control that opens or closes the panel.
    this.updateComplete.then(() =>
      this.shadowRoot
        ?.querySelector<HTMLElement>(open ? ".schedules-close" : ".schedules-open")
        ?.focus(),
    );
  }

  /**
   * Bar at the foot of the card, and the panel it slides up over the card:
   * a tab per day mode with the 24 h timelines of its schedules, and the
   * scheduler card to edit them. The card keeps its height, so the
   * dashboard around it does not move.
   */
  private _renderSchedules(dayMode: string, dayModes: string[]) {
    const title = localize(this.hass, "schedule.title");
    const bar = (open: boolean) => html`<button
      type="button"
      class="schedules-bar ${open ? "schedules-close" : "schedules-open"}"
      aria-expanded=${open ? "true" : "false"}
      aria-controls="schedules-panel"
      @click=${() => this._toggleSchedules(!open)}
    >
      <ha-icon icon="mdi:calendar-clock"></ha-icon>
      <span class="schedules-title">${title}</span>
      <span class="schedules-mode">${dayMode}</span>
      <ha-icon
        class="chevron"
        icon=${open ? "mdi:chevron-down" : "mdi:chevron-up"}
      ></ha-icon>
    </button>`;
    return html`${bar(false)}
      ${this._schedulesOpen
        ? html`<div
            id="schedules-panel"
            class="schedules-panel"
            role="region"
            aria-label=${title}
            @keydown=${(ev: KeyboardEvent) => {
              if (ev.key !== "Escape") return;
              ev.stopPropagation();
              this._toggleSchedules(false);
            }}
          >
            ${bar(true)}
            <div class="schedules-body">
              <homeshift-schedule-panel
                .hass=${this.hass}
                .schedules=${this._schedules ?? []}
                .modes=${dayModes}
                .activeMode=${dayMode}
                .entities=${this._config.schedule_entities ?? []}
              ></homeshift-schedule-panel>
            </div>
          </div>`
        : nothing}`;
  }

  private _pickDay(entityId: string, option: string) {
    this._closeDayList();
    void callService(this, this.hass, "card.select_failed", "select", "select_option", {
      entity_id: entityId,
      option,
    });
  }

  private _openDayList(entries: [string, string][], current: string) {
    this._dayActive = Math.max(
      0,
      entries.findIndex(([, display]) => display === current),
    );
    this._dayOpen = true;
  }

  private _closeDayList() {
    this._dayOpen = false;
  }

  /**
   * Keyboard of the day mode combobox: the focus stays on the button and
   * the arrows move the highlighted option (aria-activedescendant).
   */
  private _onDayKeydown(
    ev: KeyboardEvent,
    entityId: string,
    entries: [string, string][],
    current: string,
  ) {
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      if (!this._dayOpen) {
        this._openDayList(entries, current);
        return;
      }
      const step = ev.key === "ArrowDown" ? 1 : entries.length - 1;
      this._dayActive = (this._dayActive + step) % entries.length;
    } else if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      if (this._dayOpen) {
        this._pickDay(entityId, entries[this._dayActive][1]);
      } else {
        this._openDayList(entries, current);
      }
    } else if (ev.key === "Escape" && this._dayOpen) {
      ev.stopPropagation();
      this._closeDayList();
    }
  }

  /** Day mode as a combobox styled like the rest of the card. */
  private _renderDayMode(day: any, entries: [string, string][]) {
    const label = localize(this.hass, "card.day_mode");
    const usable = isUsable(day);
    const currentKey = entries.find(([, display]) => display === day.state)?.[0];
    const icon = (key?: string) =>
      (key && DAY_ICONS[key]) || "mdi:calendar-today";
    return html`<div
      class="tile day-mode"
      @focusout=${(ev: FocusEvent) => {
        const next = ev.relatedTarget as Node | null;
        if (!next || !(ev.currentTarget as HTMLElement).contains(next)) {
          this._closeDayList();
        }
      }}
    >
      <button
        type="button"
        class="day-mode-button"
        role="combobox"
        aria-label=${label}
        aria-haspopup="listbox"
        aria-controls="day-mode-list"
        aria-expanded=${this._dayOpen ? "true" : "false"}
        aria-activedescendant=${this._dayOpen
          ? `day-mode-${this._dayActive}`
          : nothing}
        ?disabled=${!usable}
        @click=${() =>
          this._dayOpen
            ? this._closeDayList()
            : this._openDayList(entries, day.state)}
        @keydown=${(ev: KeyboardEvent) =>
          this._onDayKeydown(ev, day.entity_id, entries, day.state)}
      >
        <span class="tile-key">${label}</span>
        <span class="tile-value">
          <ha-icon class="day-icon" icon=${icon(currentKey)}></ha-icon>
          <span class="tile-text">${usable ? day.state : localize(this.hass, "card.unavailable")}</span>
          <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
        </span>
      </button>
      ${this._dayOpen
        ? html`<ul id="day-mode-list" class="day-mode-list" role="listbox" aria-label=${label}>
            ${entries.map(([key, display], index) => {
              const selected = display === day.state;
              return html`<li
                id="day-mode-${index}"
                class="day-mode-option ${index === this._dayActive ? "active" : ""}"
                role="option"
                aria-selected=${selected ? "true" : "false"}
                @mousedown=${(ev: Event) => ev.preventDefault()}
                @mousemove=${() => (this._dayActive = index)}
                @click=${() => this._pickDay(day.entity_id, display)}
              >
                <ha-icon icon=${icon(key)}></ha-icon>
                <span class="option-text">${display}</span>
                <ha-icon class="check" icon="mdi:check"></ha-icon>
              </li>`;
            })}
          </ul>`
        : nothing}
    </div>`;
  }

  private onThermostatSelect(entityId: string, option: string) {
    void callService(this, this.hass, "card.select_failed", "select", "select_option", {
      entity_id: entityId,
      option,
    });
  }

  /**
   * Service call behind the "open now" / "close now" buttons, or undefined
   * when the cover time must stay a plain label.
   *
   * Priority: a legacy `cover_entity`, when set, wins (cover.open_cover /
   * close_cover on that cover, kept for existing dashboards); otherwise the
   * integration's buttons (`open_covers_entity` / `close_covers_entity`)
   * are pressed. A button's state is the time of its last press ("unknown"
   * if never pressed), so only a missing or unavailable button disables it.
   */
  private _coverCall(
    action: CoverAction,
  ): { domain: string; service: string; entity_id: string } | undefined {
    const coverId = this._config.cover_entity;
    if (coverId) {
      return isUsable(this.getEntityState(coverId))
        ? { domain: "cover", service: `${action}_cover`, entity_id: coverId }
        : undefined;
    }
    const buttonId =
      action === "open"
        ? this._config.open_covers_entity
        : this._config.close_covers_entity;
    const button = this.getEntityState(buttonId);
    return button && button.state !== "unavailable"
      ? { domain: "button", service: "press", entity_id: buttonId! }
      : undefined;
  }

  private async onCoverAction(action: CoverAction) {
    const call = this._coverCall(action);
    if (!call || this._coverPending) return;
    this._coverPending = action;
    try {
      // Keep the "sending" state visible briefly even when HA answers at
      // once, so the tap gets a feedback.
      await Promise.all([
        this.hass.callService(call.domain, call.service, {
          entity_id: call.entity_id,
        }),
        new Promise((resolve) =>
          setTimeout(resolve, HomeShiftCard.COVER_FEEDBACK_MS),
        ),
      ]);
    } catch (err) {
      notifyFailure(this, this.hass, `card.cover_${action}_failed`, err);
    } finally {
      this._coverPending = undefined;
    }
  }

  private _renderCoverTime(action: CoverAction, time: string) {
    if (!this._coverCall(action)) {
      return html`<span
        class="cover-time ${action}"
        title=${localize(this.hass, `card.cover_${action}_time`)}
      >
        ${coverIcon(action)}${time}
      </span>`;
    }
    const pending = this._coverPending === action;
    const label = localize(this.hass, `card.cover_${action}_action`, { time });
    return html`<button
      type="button"
      class="cover-time ${action} actionable ${pending ? "pending" : ""}"
      title=${label}
      aria-label=${label}
      aria-busy=${pending ? "true" : "false"}
      ?disabled=${this._coverPending !== undefined}
      @click=${() => this.onCoverAction(action)}
    >
      ${coverIcon(action)}${pending
        ? localize(this.hass, "card.cover_sending")
        : time}
    </button>`;
  }

  private _formatAbsoluteTime(isoString?: string): string {
    if (!isoString) return "";
    const dt = new Date(isoString);
    if (isNaN(dt.getTime())) return "";
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const timeStr = formatTime(dt, this.hass?.locale);
    if (dt.toDateString() === now.toDateString()) {
      return `${localize(this.hass, "card.today")} ${timeStr}`;
    }
    if (dt.toDateString() === tomorrow.toDateString()) {
      return `${localize(this.hass, "card.tomorrow")} ${timeStr}`;
    }
    return `${formatShortDate(dt, this.hass?.locale)} ${timeStr}`;
  }

  private _settingLabel(minutes: number | undefined): string {
    if (minutes === undefined) return localize(this.hass, "card.unavailable");
    if (!minutes) return localize(this.hass, "card.duration_off");
    return formatMinutes(minutes);
  }

  private _clockIn(minutes: number): string {
    return formatTime(
      new Date(Date.now() + minutes * 60000),
      this.hass?.locale,
    );
  }

  private _clockAt(isoString: string, shiftMinutes = 0): string {
    const at = new Date(new Date(isoString).getTime() + shiftMinutes * 60000);
    return formatTime(at, this.hass?.locale);
  }

  /** Open one setting at a time, and fold it back once it is left alone. */
  private _toggleSetting(name: SettingName) {
    this._openSetting = this._openSetting === name ? null : name;
    this._armSettingTimeout();
  }

  private _armSettingTimeout() {
    clearTimeout(this._settingTimeout);
    if (!this._openSetting) return;
    // Picking covers one by one takes longer than nudging a stepper.
    const delay = this._openSetting === "covers" ? 20000 : 6000;
    this._settingTimeout = setTimeout(() => {
      this._openSetting = null;
    }, delay);
  }

  private _stepSetting(
    name: "override" | "early",
    presets: number[],
    current: number,
    direction: 1 | -1,
  ) {
    const entityId =
      name === "override"
        ? this._config.override_duration_entity
        : this._config.early_switch_entity;
    if (!entityId) return;
    // The stored value may sit between two presets (25 min set from the
    // entity page): land on the nearest preset in the direction asked for,
    // 30 going up and 15 going down.
    const next =
      direction > 0
        ? presets.find((value) => value > current)
        : [...presets].reverse().find((value) => value < current);
    if (next === undefined) return;
    this._armSettingTimeout();
    void callService(this, this.hass, "card.set_value_failed", "number", "set_value", {
      entity_id: entityId,
      value: next,
    });
  }

  /**
   * Collapsible minutes setting. `current` is undefined while the number
   * entity is unknown or unavailable: the value then reads "Unavailable",
   * is not highlighted and the setting cannot be opened (no NaN, no
   * stepping from a value that does not exist).
   */
  private _renderSetting(
    name: "override" | "early",
    icon: string,
    label: string,
    effect: string,
    presets: number[],
    current: number | undefined,
  ) {
    const open = current !== undefined && this._openSetting === name;
    return html`<div class="setting ${open ? "open" : ""}">
      <button
        class="setting-head"
        aria-expanded=${open ? "true" : "false"}
        ?disabled=${current === undefined}
        @click=${() => this._toggleSetting(name)}
      >
        <ha-icon icon="${icon}"></ha-icon>
        <span class="setting-label">${label}</span>
        <span class="setting-value ${current ? "set" : ""}"
          >${this._settingLabel(current)}</span
        >
        <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
      </button>
      ${open
        ? html`<div class="setting-body">
            <div class="stepper">
              <button
                aria-label=${localize(this.hass, "card.decrease", {
                  setting: label,
                })}
                ?disabled=${current <= presets[0]}
                @click=${() =>
                  this._stepSetting(name, presets, current, -1)}
              >
                −
              </button>
              <span class="stepper-value" aria-live="polite"
                >${this._settingLabel(current)}</span
              >
              <button
                aria-label=${localize(this.hass, "card.increase", {
                  setting: label,
                })}
                ?disabled=${current >= presets[presets.length - 1]}
                @click=${() => this._stepSetting(name, presets, current, 1)}
              >
                +
              </button>
            </div>
            <p class="setting-effect">${effect}</p>
          </div>`
        : nothing}
    </div>`;
  }

  /**
   * Minutes held by a number entity, as `_renderSetting` expects them, or
   * null when the setting gets no row at all: not configured, or configured
   * but missing outside the card picker preview.
   */
  private _minutes(entityId?: string): number | undefined | null {
    if (!entityId) return null;
    const stateObj = this.getEntityState(entityId);
    if (!stateObj) return this.preview ? 0 : null;
    return numericState(stateObj);
  }

  /**
   * Options of a HomeShift select as [key, display] pairs: from its
   * option_map (integration ≥ 1.1.0), else its options keyed by themselves.
   */
  private _entries(stateObj: any): [string, string][] {
    const map: Record<string, string> = stateObj.attributes?.option_map ?? {};
    return Object.keys(map).length > 0
      ? (Object.entries(map) as [string, string][])
      : (stateObj.attributes?.options ?? []).map(
          (o: string) => [o, o] as [string, string],
        );
  }

  /** Thermostat mode in force, as [key, display], while the select is usable. */
  private _activeThermo(thermo: any): [string, string] | undefined {
    if (!isUsable(thermo)) return undefined;
    const activeKey: string | undefined = thermo.attributes?.current_key;
    return this._entries(thermo).find(([key, display]) =>
      activeKey ? key === activeKey : display === thermo.state,
    );
  }

  private _renderMain(
    thermo: any,
    day: any,
    heatProtectionActive: boolean,
    coversLeftOpen: string[],
    coverInhibitions: CoverInhibitions,
    coverOpenTime?: string,
    coverCloseTime?: string,
  ) {
    const dayEntries = this._entries(day);
    // Thermostat presets, keyed so each can carry its own colour and its own
    // translation regardless of the display values set in the integration.
    const thermoEntries = this._entries(thermo);

    const nextMode = this.getEntityState(this._config.next_mode_entity);
    const nextModeAt = this.getEntityState(this._config.next_mode_at_entity);
    const earlySwitch = this._minutes(this._config.early_switch_entity);
    const override = this._minutes(this._config.override_duration_entity);

    // The next-mode sensors are unknown when no switch is scheduled.
    const hasNextMode = isUsable(nextMode);
    const nextModeName = hasNextMode ? nextMode!.state : "";
    const nextModeAtText = isUsable(nextModeAt)
      ? this._formatAbsoluteTime(nextModeAt!.state)
      : "";
    const hasNextAt = nextModeAtText !== "";

    const overrideEffect = override
      ? localize(this.hass, "card.override_effect", {
          duration: this._settingLabel(override),
          time: this._clockIn(override),
        })
      : localize(this.hass, "card.override_none");
    const earlyEffect = !hasNextAt
      ? localize(this.hass, "card.early_no_event")
      : earlySwitch
        ? localize(this.hass, "card.early_effect", {
            mode: nextModeName,
            time: this._clockAt(nextModeAt!.state),
            scheduled: this._clockAt(nextModeAt!.state, earlySwitch),
          })
        : localize(this.hass, "card.early_none", {
            mode: nextModeName,
            time: this._clockAt(nextModeAt!.state),
          });

    const hasCoverOpenTime = isUsable(coverOpenTime);
    const hasCoverCloseTime = isUsable(coverCloseTime);
    const coversFull = localize(this.hass, "card.covers_left_open", {
      covers: coversLeftOpen.join(", "),
    });
    // Past three, the names stop fitting on one line: the chip shows a count
    // and becomes a button that reveals the names (touch has no hover).
    const coversTruncated = coversLeftOpen.length > 3;
    const coversSummary = coversTruncated
      ? localize(this.hass, "card.covers_left_open_count", {
          count: String(coversLeftOpen.length),
        })
      : coversFull;

    const pausedCovers = [...coverInhibitions.inhibited.keys()].map((id) =>
      this._friendlyName(id),
    );
    const pausedSummary =
      pausedCovers.length > 2
        ? localize(this.hass, "card.covers_paused_count", {
            count: String(pausedCovers.length),
          })
        : localize(this.hass, "card.covers_paused", {
            covers: pausedCovers.join(", "),
          });
    const pausedDetail = [...coverInhibitions.inhibited.entries()]
      .map(([id, until]) => `${this._friendlyName(id)} — ${this._inhibitEnd(until)}`)
      .join("\n");

    const active = this._activeThermo(thermo);
    const thermoUsable = isUsable(thermo);
    const heatPumps = this.getHeatPumps();

    return html`
      <div class="rows">
        <div
          class="presets"
          role="group"
          aria-label=${localize(this.hass, "card.thermostat_mode")}
        >
          ${thermoEntries.map(([key, display]) => {
            const on = active?.[0] === key;
            const mode = this._presetClass(key, display);
            const style = MODE_STYLES[mode] ?? NEUTRAL_MODE;
            return html`<button
              class="preset preset--${mode} ${on ? "on" : ""}"
              style="--c: ${style.rgb}"
              aria-pressed=${on ? "true" : "false"}
              ?disabled=${!thermoUsable}
              @click=${() => this.onThermostatSelect(thermo.entity_id, display)}
            >
              <ha-icon icon=${style.icon}></ha-icon>
              <span class="preset-label"
                >${localize(this.hass, `thermostat.${key}`, undefined, display)}</span
              >
            </button>`;
          })}
        </div>

        <div class="tiles">
          ${this._renderDayMode(day, dayEntries)}
          ${hasNextMode || hasNextAt
            ? html`<div class="tile next-row">
                <span class="tile-key">${localize(this.hass, "card.next")}</span>
                <span class="tile-value">
                  <span class="tile-text">${nextModeName}</span>
                  <span class="next-at">${nextModeAtText}</span>
                </span>
              </div>`
            : nothing}
        </div>

        ${override !== null
          ? this._renderSetting(
              "override",
              "mdi:hand-back-left",
              localize(this.hass, "card.override_label"),
              overrideEffect,
              HomeShiftCard.OVERRIDE_PRESETS,
              override,
            )
          : nothing}
        ${earlySwitch !== null
          ? this._renderSetting(
              "early",
              "mdi:clock-fast",
              localize(this.hass, "card.early_label"),
              earlyEffect,
              HomeShiftCard.EARLY_SWITCH_PRESETS,
              earlySwitch,
            )
          : nothing}

        ${hasCoverOpenTime || hasCoverCloseTime
          ? html`<div class="row covers-row">
              <span class="row-key">${localize(this.hass, "card.covers")}</span>
              <span class="cover-times">
                ${hasCoverOpenTime
                  ? this._renderCoverTime("open", coverOpenTime!)
                  : nothing}
                ${hasCoverCloseTime
                  ? this._renderCoverTime("close", coverCloseTime!)
                  : nothing}
              </span>
            </div>`
          : nothing}

        ${coverInhibitions.managed.length > 0
          ? this._renderCoverInhibition(coverInhibitions)
          : nothing}

        ${heatPumps.length > 0
          ? this._renderHeatPumps(heatPumps, active?.[0] === "off")
          : nothing}

        ${heatProtectionActive ||
        coversLeftOpen.length > 0 ||
        pausedCovers.length > 0
          ? html`<div class="alerts">
              ${heatProtectionActive
                ? html`<span class="chip chip--heat">
                    <ha-icon icon="mdi:white-balance-sunny"></ha-icon>
                    ${localize(this.hass, "card.heat_protection_active")}
                  </span>`
                : nothing}
              ${coversLeftOpen.length > 0 && !coversTruncated
                ? html`<span class="chip chip--covers">
                    <ha-icon icon="mdi:window-shutter-alert"></ha-icon>
                    ${coversSummary}
                  </span>`
                : nothing}
              ${coversTruncated
                ? html`<button
                    type="button"
                    class="chip chip--covers"
                    title=${coversFull}
                    aria-label=${coversFull}
                    aria-expanded=${this._coversExpanded ? "true" : "false"}
                    @click=${() =>
                      (this._coversExpanded = !this._coversExpanded)}
                  >
                    <ha-icon icon="mdi:window-shutter-alert"></ha-icon>
                    ${coversSummary}
                  </button>`
                : nothing}
              ${pausedCovers.length > 0
                ? html`<button
                    type="button"
                    class="chip chip--paused"
                    title=${pausedDetail}
                    @click=${() => {
                      this._openSetting = "covers";
                      this._armSettingTimeout();
                    }}
                  >
                    <ha-icon icon="mdi:window-shutter-cog"></ha-icon>
                    ${pausedSummary}
                  </button>`
                : nothing}
            </div>
            ${coversTruncated && this._coversExpanded
              ? html`<p class="covers-detail">${coversFull}</p>`
              : nothing}`
          : nothing}
      </div>
    `;
  }

  protected render() {
    if (!this.hass || !this._config) return nothing;

    const dayRaw = this.getEntityState(this._config.day_mode_entity);
    const thermoRaw = this.getEntityState(this._config.thermostat_mode_entity);

    // Stub data is only for the card picker / editor preview: on a real
    // dashboard a missing entity (typo, integration not loaded) must say so
    // rather than show a card that looks functional.
    if (!this.preview) {
      const missing = [
        [this._config.day_mode_entity, dayRaw],
        [this._config.thermostat_mode_entity, thermoRaw],
      ]
        .filter(([, stateObj]) => !stateObj)
        .map(([entityId]) => entityId || "?");
      if (missing.length > 0) {
        return html`
          <ha-card>
            ${missing.map(
              (entity) =>
                html`<div class="error">
                  ${localize(this.hass, "card.entity_not_found", { entity })}
                </div>`,
            )}
          </ha-card>
        `;
      }
    }

    const day = dayRaw ?? {
      entity_id: this._config.day_mode_entity,
      state: localize(this.hass, "preview.work"),
      attributes: {
        option_map: Object.fromEntries(
          ["home", "work", "remote", "away"].map((key) => [
            key,
            localize(this.hass, `preview.${key}`),
          ]),
        ),
      },
    };

    const thermo = thermoRaw ?? {
      entity_id: this._config.thermostat_mode_entity,
      state: localize(this.hass, "thermostat.heating"),
      attributes: {
        option_map: Object.fromEntries(
          ["off", "heating", "cooling", "ventilation"].map((key) => [
            key,
            localize(this.hass, `thermostat.${key}`),
          ]),
        ),
        current_key: "heating",
      },
    };

    const heatProtectionActive =
      this.getEntityState(this._config.heat_protection_entity)?.state === "on";
    const coverOpenTime = this.getEntityState(
      this._config.cover_open_time_entity,
    )?.state;
    const coverCloseTime = this.getEntityState(
      this._config.cover_close_time_entity,
    )?.state;

    const dayModes: string[] = day.attributes?.options ?? [];
    const showSchedules = isUsable(day) && this._hasDaySchedules(dayModes);

    // The card takes the colour of the thermostat mode in force.
    const active = this._activeThermo(thermo);
    const mode = active ? this._presetClass(active[0], active[1]) : "none";
    const style = MODE_STYLES[mode] ?? NEUTRAL_MODE;
    const modeLabel = active
      ? localize(this.hass, `thermostat.${active[0]}`, undefined, active[1])
      : localize(this.hass, "card.unavailable");
    const animated = ["heating", "cooling", "ventilation"].includes(mode);

    return html`
      <ha-card data-mode=${mode} style="--m: ${style.rgb}">
        <div class="glow" aria-hidden="true"></div>
        ${animated
          ? html`<div class="particles" aria-hidden="true">
              ${PARTICLES.map(
                ([left, duration, delay, drift, top]) =>
                  html`<span
                    class="particle"
                    style="left: ${left}%; --y: ${top}%; --d: ${duration}s; --dl: ${delay}s; --dx: ${drift}px"
                  ></span>`,
              )}
            </div>`
          : nothing}
        <div class="container" ?inert=${showSchedules && this._schedulesOpen}>
          <div class="header">
            <span class="badge"><ha-icon icon=${style.icon}></ha-icon></span>
            <span class="heading">
              <span class="name">${this._config.name}</span>
              <span class="status">
                <span class="dot"></span>${modeLabel} · ${isUsable(day)
                  ? day.state
                  : localize(this.hass, "card.unavailable")}
              </span>
            </span>
          </div>
          ${this._renderCalendarError(day)}
          ${this._renderMain(
            thermo,
            day,
            heatProtectionActive,
            this.getCoversLeftOpen(),
            this.getCoverInhibitions(),
            coverOpenTime,
            coverCloseTime,
          )}
        </div>
        ${showSchedules ? this._renderSchedules(day.state, dayModes) : nothing}
      </ha-card>
    `;
  }

  /** Warns when the calendars cannot be read: the day mode is then only kept. */
  private _renderCalendarError(day: any) {
    const error = day?.attributes?.calendar_error;
    if (!error) return nothing;
    const since = new Date(error.since);
    const time = Number.isNaN(since.getTime())
      ? ""
      : formatTime(since, this.hass?.locale);
    return html`<div class="calendar-error" role="alert">
      <ha-icon icon="mdi:calendar-remove"></ha-icon>
      <span>
        <strong>${localize(this.hass, "card.calendar_unreadable")}</strong>
        <span>${localize(this.hass, "card.calendar_unreadable_detail", {
          time,
          mode: day?.state ?? "",
        })}</span>
      </span>
    </div>`;
  }

  static styles = cardStyles;
}

if (!customElements.get("homeshift-card")) {
  customElements.define("homeshift-card", HomeShiftCard);
}

export { HomeShiftCard };
