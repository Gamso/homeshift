import { LitElement, html, svg, css, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import { localize } from "../localize/localize";
import "./homeshift-card-editor";
import { ENTITY_FIELDS, HomeShiftCardConfig } from "../types";
import { discoverEntities } from "../entities";
import { formatMinutes, isUsable, numericState } from "../state";
import { callService, notifyFailure } from "../notify";
import {
  daysBetween,
  formatShortDate,
  formatTime,
  secondsOfDay,
  timeZone,
} from "../time";
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
  /** Time zone the midnight refresh was computed in. */
  private _zone?: string;
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
    // Midnight in Home Assistant's time zone, one second past.
    const zone = timeZone(this.hass);
    this._zone = zone;
    const delay =
      (86_400 - secondsOfDay(now, zone) + 1) * 1000 - now.getMilliseconds();
    this._midnightTimer = setTimeout(() => {
      this._day++;
      this._scheduleMidnightRefresh();
    }, delay);
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
      if (this.isConnected && timeZone(this.hass) !== this._zone) {
        this._scheduleMidnightRefresh();
      }
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
    const zone = timeZone(this.hass);
    const timeStr = formatTime(dt, this.hass?.locale, zone);
    const days = daysBetween(new Date(), dt, zone);
    if (days === 0) {
      return `${localize(this.hass, "card.today")} ${timeStr}`;
    }
    if (days === 1) {
      return `${localize(this.hass, "card.tomorrow")} ${timeStr}`;
    }
    return `${formatShortDate(dt, this.hass?.locale, zone)} ${timeStr}`;
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
      timeZone(this.hass),
    );
  }

  private _clockAt(isoString: string, shiftMinutes = 0): string {
    const at = new Date(new Date(isoString).getTime() + shiftMinutes * 60000);
    return formatTime(at, this.hass?.locale, timeZone(this.hass));
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
      : formatTime(since, this.hass?.locale, timeZone(this.hass));
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

  static styles = css`
    .calendar-error {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      margin: 0 0 10px;
      padding: 9px 11px;
      border-radius: 10px;
      border: 1px solid rgba(255, 170, 40, 0.45);
      background: rgba(255, 170, 40, 0.13);
      color: #ffd98f;
      font-size: 13px;
      line-height: 1.4;
    }
    .calendar-error ha-icon {
      --mdc-icon-size: 18px;
      flex: none;
      margin-top: 1px;
    }
    .calendar-error strong {
      display: block;
      font-weight: 500;
    }
    .calendar-error span span {
      font-size: 12px;
      color: #e9c486;
    }
    /* Dark glass card: its colour (--m, "r, g, b") follows the thermostat mode. */
    ha-card {
      --m: 148, 163, 184;
      --hs-text: #e6f2f5;
      --hs-text-2: rgba(220, 235, 240, 0.62);
      --hs-surface: rgba(255, 255, 255, 0.06);
      --hs-ring: rgba(255, 255, 255, 0.07);
      /* What the panel and the scheduler card read from the theme follows
         the dark card instead. */
      --primary-text-color: var(--hs-text);
      --secondary-text-color: var(--hs-text-2);
      --divider-color: rgba(255, 255, 255, 0.08);
      --card-background-color: #121a24;
      --ha-card-background: #121a24;
      position: relative;
      /* Clips the glow, the particles and the schedules panel. */
      overflow: hidden;
      padding: 0;
      border-radius: var(--ha-card-border-radius, 20px);
      border: 1px solid rgba(var(--m), 0.25);
      background: linear-gradient(
        160deg,
        rgba(20, 28, 38, 0.96),
        rgba(10, 15, 22, 0.98)
      );
      box-shadow:
        0 8px 26px rgba(0, 0, 0, 0.35),
        0 0 22px -6px rgba(var(--m), 0.45),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
      color: var(--hs-text);
      transition:
        border-color 0.6s,
        box-shadow 0.6s;
    }

    button {
      font-family: inherit;
    }

    button:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }

    /* Ambience: a glow where the heat rises, the cold falls or the air blows. */
    .glow {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: radial-gradient(
        110% 70% at 50% 50%,
        rgba(var(--m), 0.22),
        transparent 75%
      );
      animation: breathe 5s ease-in-out infinite;
    }

    ha-card[data-mode="heating"] .glow {
      background: radial-gradient(
        130% 75% at 50% 110%,
        rgba(255, 110, 30, 0.45),
        rgba(255, 80, 20, 0.12) 55%,
        transparent 78%
      );
    }

    ha-card[data-mode="cooling"] .glow {
      background: radial-gradient(
        120% 70% at 50% -10%,
        rgba(80, 190, 255, 0.4),
        rgba(60, 140, 255, 0.1) 55%,
        transparent 75%
      );
    }

    ha-card[data-mode="ventilation"] .glow {
      background: radial-gradient(
        120% 80% at 0% 50%,
        rgba(45, 212, 160, 0.35),
        rgba(45, 212, 160, 0.09) 55%,
        transparent 78%
      );
    }

    ha-card[data-mode="off"] .glow {
      background: radial-gradient(
        110% 70% at 50% 50%,
        rgba(148, 163, 184, 0.18),
        rgba(71, 85, 105, 0.1) 60%,
        transparent 80%
      );
      animation-duration: 9s;
    }

    .particles {
      position: absolute;
      inset: 0;
      overflow: hidden;
      pointer-events: none;
    }

    .particle {
      position: absolute;
      opacity: 0;
    }

    ha-card[data-mode="heating"] .particle {
      bottom: 0;
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: radial-gradient(circle, #ffe0a0, #ff7a2a 60%, transparent 70%);
      box-shadow: 0 0 6px 1px rgba(255, 120, 40, 0.7);
      animation: rise var(--d) ease-in var(--dl) infinite;
    }

    ha-card[data-mode="cooling"] .particle {
      top: 0;
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: radial-gradient(circle, #fff, #bfe9ff 55%, transparent 72%);
      animation: fall calc(var(--d) * 1.5) linear var(--dl) infinite;
    }

    ha-card[data-mode="ventilation"] .particle {
      top: var(--y);
      width: 34px;
      height: 2px;
      border-radius: 2px;
      background: linear-gradient(
        90deg,
        transparent,
        rgba(170, 255, 225, 0.75),
        transparent
      );
      animation: breeze var(--d) linear var(--dl) infinite;
    }

    @keyframes breathe {
      50% {
        opacity: 0.6;
      }
    }

    @keyframes rise {
      from {
        transform: translate(0, 0) scale(1);
        opacity: 0.9;
      }
      to {
        transform: translate(var(--dx), -260px) scale(0.3);
        opacity: 0;
      }
    }

    @keyframes fall {
      from {
        transform: translate(0, -10px);
        opacity: 0.9;
      }
      to {
        transform: translate(var(--dx), 320px);
        opacity: 0;
      }
    }

    @keyframes breeze {
      from {
        left: -40px;
        opacity: 0;
      }
      20% {
        opacity: 0.8;
      }
      to {
        left: 100%;
        opacity: 0;
      }
    }

    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }

    .container {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 14px;
    }

    .rows {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .badge {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      border-radius: 12px;
      background: rgba(var(--m), 0.16);
      box-shadow: inset 0 0 0 1px rgba(var(--m), 0.25);
      color: rgb(var(--m));
      --mdc-icon-size: 21px;
      transition:
        background 0.4s,
        color 0.4s;
    }

    ha-card[data-mode="ventilation"] .badge ha-icon {
      animation: spin 1.6s linear infinite;
    }

    .heading {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 15px;
      font-weight: 600;
      line-height: 1.2;
    }

    .status {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 2px;
      font-size: 12px;
      color: var(--hs-text-2);
    }

    .dot {
      flex: none;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: rgb(var(--m));
      box-shadow: 0 0 6px rgb(var(--m));
    }

    /* Thermostat modes: one segmented control, one colour (--c) per mode. */
    .presets {
      display: flex;
      gap: 4px;
      padding: 3px;
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.28);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
    }

    .preset {
      flex: 1 1 0;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      height: 48px;
      padding: 0 2px;
      border: 0;
      border-radius: 11px;
      background: transparent;
      color: var(--hs-text-2);
      font-size: 11.5px;
      font-weight: 500;
      cursor: pointer;
      --mdc-icon-size: 19px;
      transition:
        background 0.3s,
        color 0.3s,
        box-shadow 0.3s;
    }

    .preset-label {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .preset:hover:not(:disabled):not(.on) {
      background: rgba(255, 255, 255, 0.06);
      color: rgb(var(--c));
    }

    .preset.on {
      color: #fff;
      background: linear-gradient(
        180deg,
        rgba(var(--c), 0.95),
        rgba(var(--c), 0.7)
      );
      box-shadow: 0 3px 12px -2px rgba(var(--c), 0.6);
    }

    .preset:disabled {
      cursor: default;
      opacity: 0.5;
    }

    /* Day mode and next mode, side by side. */
    .tiles {
      position: relative;
      /* The day mode list opens over the rows below. */
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
      gap: 6px;
    }

    .tile {
      position: relative;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
      padding: 8px 10px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
    }

    .tile.day-mode {
      padding: 0;
      background: none;
      box-shadow: none;
    }

    .day-mode-button {
      all: unset;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      gap: 3px;
      width: 100%;
      padding: 8px 10px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      cursor: pointer;
      transition:
        background 0.2s,
        box-shadow 0.2s;
    }

    .day-mode-button:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
    }

    .day-mode-button[aria-expanded="true"] {
      background: rgba(var(--m), 0.12);
      box-shadow: inset 0 0 0 1px rgba(var(--m), 0.5);
    }

    .day-mode-button:disabled {
      cursor: default;
      opacity: 0.6;
    }

    .tile-key,
    .row-key {
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--hs-text-2);
    }

    .tile-value {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      font-size: 13px;
      font-weight: 500;
    }

    .tile-text {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .day-icon {
      flex: none;
      --mdc-icon-size: 16px;
      color: rgb(var(--m));
    }

    .tile-value .chevron {
      flex: none;
      --mdc-icon-size: 18px;
      color: var(--hs-text-2);
      transition: transform 0.2s;
    }

    .day-mode-button[aria-expanded="true"] .chevron {
      transform: rotate(180deg);
      color: rgb(var(--m));
    }

    .next-at {
      flex: none;
      font-size: 12px;
      font-weight: 400;
      color: var(--hs-text-2);
    }

    .day-mode-list {
      position: absolute;
      left: 0;
      right: 0;
      top: calc(100% + 6px);
      margin: 0;
      padding: 4px;
      list-style: none;
      border-radius: 12px;
      background: rgba(18, 26, 36, 0.98);
      box-shadow:
        inset 0 0 0 1px rgba(255, 255, 255, 0.08),
        0 12px 30px rgba(0, 0, 0, 0.5);
      animation: pop 0.15s ease-out;
    }

    .day-mode-option {
      display: flex;
      align-items: center;
      gap: 8px;
      height: 34px;
      padding: 0 10px;
      border-radius: 9px;
      font-size: 13px;
      cursor: pointer;
      --mdc-icon-size: 16px;
    }

    .day-mode-option ha-icon {
      flex: none;
      color: var(--hs-text-2);
    }

    .option-text {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .day-mode-option .check {
      visibility: hidden;
    }

    .day-mode-option.active {
      background: rgba(255, 255, 255, 0.07);
    }

    .day-mode-option[aria-selected="true"] {
      background: rgba(var(--m), 0.18);
    }

    .day-mode-option[aria-selected="true"].active {
      background: rgba(var(--m), 0.26);
    }

    .day-mode-option[aria-selected="true"] ha-icon {
      visibility: visible;
      color: rgb(var(--m));
    }

    @keyframes pop {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
    }

    /* Collapsed by default: the value is readable without opening anything. */
    .setting {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .setting-head {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      height: 36px;
      padding: 0 10px;
      border: 0;
      border-radius: 11px;
      background: var(--hs-surface);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
      font-size: 12.5px;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
    }

    .setting-head:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
    }

    .setting-head:disabled {
      cursor: default;
    }

    .setting-head:disabled .chevron {
      visibility: hidden;
    }

    .setting-head ha-icon {
      flex-shrink: 0;
      --mdc-icon-size: 17px;
      color: var(--hs-text-2);
    }

    .setting-label {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .setting-value {
      color: var(--hs-text-2);
    }

    .setting-value.set {
      color: rgb(var(--m));
    }

    .setting .chevron {
      transition: transform 0.15s ease;
    }

    .setting.open .chevron {
      transform: rotate(180deg);
    }

    .setting-body {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 10px;
      border-radius: 11px;
      background: rgba(0, 0, 0, 0.22);
      animation: fadeIn 0.15s ease;
    }

    .stepper {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
    }

    .stepper button {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 34px;
      height: 34px;
      border: 0;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
      color: var(--hs-text);
      font-size: 18px;
      line-height: 1;
      cursor: pointer;
    }

    .stepper button:active:not(:disabled) {
      transform: scale(0.9);
      background: rgba(var(--m), 0.3);
    }

    .stepper button:disabled {
      opacity: 0.35;
      cursor: default;
    }

    .stepper-value {
      min-width: 70px;
      text-align: center;
      font-size: 20px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    .setting-effect {
      margin: 0;
      font-size: 12px;
      line-height: 1.4;
      text-align: center;
      color: var(--hs-text-2);
    }

    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .covers-row {
      display: grid;
      grid-template-columns: auto 1fr;
    }

    .cover-times {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      gap: 6px;
    }

    .cover-time {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      height: 40px;
      padding: 0 8px;
      border: 0;
      border-radius: 11px;
      background: var(--hs-surface);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
      font-size: 14px;
      font-weight: 500;
      font-variant-numeric: tabular-nums;
    }

    /* Roller shutter: amber when it opens, blue when it closes. */
    .cover-icon {
      flex: none;
      width: 24px;
      height: 24px;
      fill: none;
      stroke: currentColor;
      stroke-width: 1.6;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .cover-time.open .cover-icon {
      color: #ffa63d;
    }

    .cover-time.close .cover-icon {
      color: #7ea2ff;
    }

    .cover-icon .solid {
      fill: currentColor;
      fill-opacity: 0.55;
    }

    .cover-icon .fill {
      fill: currentColor;
      fill-opacity: 0.3;
      stroke: none;
    }

    .cover-icon .rails {
      stroke-width: 1.2;
      stroke-opacity: 0.5;
    }

    .cover-time.actionable {
      cursor: pointer;
    }

    .cover-time.actionable:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.1);
    }

    .cover-time.actionable:disabled {
      cursor: progress;
    }

    .cover-time.pending {
      animation: cover-pending 0.8s ease-in-out infinite alternate;
    }

    @keyframes cover-pending {
      from {
        opacity: 1;
      }
      to {
        opacity: 0.5;
      }
    }

    .error {
      position: relative;
      padding: 14px;
      color: #ff8a80;
    }

    /* Climate auto start/stop: green when VTherm may stop it, the mode's
       colour while a comfort range keeps it running, grey when not driven. */
    .heat-pumps {
      display: flex;
      flex-direction: column;
      gap: 6px;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.035);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
    }

    .heat-pumps-head {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      height: 36px;
      padding: 0 10px;
      border: 0;
      border-radius: 11px;
      background: var(--hs-surface);
      color: var(--hs-text);
      font-size: 12.5px;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
    }

    .heat-pumps-head:hover {
      background: rgba(255, 255, 255, 0.09);
    }

    .heat-pumps-head ha-icon {
      flex-shrink: 0;
      --mdc-icon-size: 17px;
      color: var(--hs-text-2);
    }

    /* The summary is what changes, so it keeps its width; a long title is the
       part cut short. */
    .heat-pumps-title {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .heat-pumps-summary {
      flex: none;
      white-space: nowrap;
      color: var(--hs-text-2);
    }

    .heat-pumps-head ha-icon.manual {
      --mdc-icon-size: 15px;
      color: #ffc24d;
    }

    .heat-pumps-head .chevron {
      transition: transform 0.15s ease;
    }

    .heat-pumps.open .heat-pumps-head .chevron {
      transform: rotate(180deg);
    }

    .heat-pump-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 0 8px 8px;
      animation: fadeIn 0.15s ease;
    }

    .heat-pump {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 8px 10px;
      border: 0;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
      text-align: left;
      cursor: pointer;
      transition: background 0.2s;
    }

    .heat-pump:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
    }

    .heat-pump:disabled {
      cursor: default;
    }

    .heat-pump-icon {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border-radius: 9px;
      --mdc-icon-size: 17px;
    }

    .heat-pump-text {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .heat-pump-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 13px;
      font-weight: 500;
    }

    .heat-pump-status {
      margin-top: 1px;
      font-size: 11.5px;
      color: var(--hs-text-2);
    }

    .heat-pump-manual {
      color: #ffc24d;
    }

    .heat-pump-tag {
      flex: none;
      display: flex;
      align-items: center;
      gap: 5px;
      height: 22px;
      padding: 0 9px;
      border-radius: 11px;
      font-size: 11.5px;
      font-weight: 500;
      --mdc-icon-size: 13px;
    }

    .heat-pump.auto .heat-pump-icon,
    .heat-pump.auto .heat-pump-tag {
      background: rgba(62, 201, 122, 0.15);
      color: #7fe0aa;
    }

    .heat-pump.auto .heat-pump-tag {
      box-shadow: inset 0 0 0 1px rgba(62, 201, 122, 0.3);
    }

    .heat-pump.comfort .heat-pump-icon,
    .heat-pump.comfort .heat-pump-tag {
      background: rgba(var(--m), 0.16);
      color: rgb(var(--m));
    }

    .heat-pump.comfort .heat-pump-tag {
      box-shadow: inset 0 0 0 1px rgba(var(--m), 0.35);
    }

    .heat-pump.idle .heat-pump-icon,
    .heat-pump.idle .heat-pump-tag {
      background: var(--hs-surface);
      color: var(--hs-text-2);
    }

    /* Alerts only exist while something is wrong; nothing is shown otherwise. */
    .alerts {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      height: 28px;
      padding: 0 11px;
      border: 0;
      border-radius: 14px;
      font-size: 12px;
      font-weight: 500;
      animation: fadeIn 0.3s ease;
    }

    .chip ha-icon {
      --mdc-icon-size: 15px;
    }

    button.chip {
      cursor: pointer;
    }

    .covers-detail {
      margin: 0;
      font-size: 12px;
      line-height: 1.4;
      color: var(--hs-text);
    }

    .chip--heat {
      background: rgba(239, 83, 80, 0.18);
      box-shadow: inset 0 0 0 1px rgba(239, 83, 80, 0.3);
      color: #ffb4b2;
      animation:
        fadeIn 0.3s ease,
        heat-pulse 2.4s ease-in-out infinite;
    }

    @keyframes heat-pulse {
      50% {
        box-shadow:
          inset 0 0 0 1px rgba(239, 83, 80, 0.5),
          0 0 10px rgba(239, 83, 80, 0.4);
      }
    }

    /* A paused cover is a choice, not a fault: calm colour, no animation. */
    .chip--paused {
      background: var(--hs-surface);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
    }

    .chip--paused ha-icon {
      color: var(--hs-text-2);
    }

    /* Pulses: a cover left up is something to act on tonight, not a steady
       status. */
    .chip--covers {
      background: rgba(255, 184, 64, 0.18);
      box-shadow: inset 0 0 0 1px rgba(255, 184, 64, 0.35);
      color: #ffc24d;
      animation:
        fadeIn 0.3s ease,
        covers-left-open-blink 1.2s ease-in-out infinite;
    }

    @keyframes covers-left-open-blink {
      50% {
        opacity: 0.55;
      }
    }

    .cover-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .cover-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      font-size: 13px;
      font-weight: 500;
    }

    .cover-name {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .cover-status {
      margin-top: 1px;
      font-size: 11.5px;
      font-weight: 400;
      color: var(--hs-text-2);
    }

    .cover-item.paused .cover-status {
      color: #ffc24d;
    }

    .cover-toggle,
    .resume-all {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
      height: 30px;
      padding: 0 11px;
      border: 0;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
      color: var(--hs-text);
      font-size: 12.5px;
      font-weight: 500;
      cursor: pointer;
    }

    .cover-toggle ha-icon {
      --mdc-icon-size: 15px;
    }

    .cover-toggle:hover,
    .resume-all:hover {
      background: rgba(255, 255, 255, 0.12);
    }

    .cover-item.paused .cover-toggle {
      background: rgba(255, 184, 64, 0.18);
      box-shadow: inset 0 0 0 1px rgba(255, 184, 64, 0.35);
      color: #ffc24d;
    }

    .resume-all {
      align-self: center;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(3px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    /* Schedules: a bar at the foot of the card, and the panel it slides up. */
    .schedules-bar {
      position: relative;
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      margin: 0;
      padding: 12px 14px;
      border: 0;
      border-top: 1px solid rgba(255, 255, 255, 0.07);
      background: transparent;
      color: var(--hs-text-2);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      text-align: left;
      cursor: pointer;
    }

    .schedules-bar:hover {
      background: rgba(255, 255, 255, 0.04);
    }

    .schedules-bar:focus-visible {
      outline-offset: -2px;
    }

    .schedules-bar ha-icon {
      flex-shrink: 0;
      --mdc-icon-size: 17px;
    }

    .schedules-title {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .schedules-mode {
      font-size: 12.5px;
      color: var(--hs-text);
      text-transform: none;
      letter-spacing: normal;
    }

    /* Anchored to the foot of the card and as tall as its content: the top
       of the card stays in sight while the schedules are shorter than it;
       longer ones scroll inside the panel. */
    .schedules-panel {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      max-height: calc(100% - 24px);
      z-index: 3;
      display: flex;
      flex-direction: column;
      border-top: 1px solid rgba(var(--m), 0.3);
      border-radius: 18px 18px 0 0;
      background: linear-gradient(
        180deg,
        rgba(18, 26, 36, 0.99),
        rgba(10, 15, 22, 0.99)
      );
      box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.4);
      animation: schedules-slide-up 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    }

    .schedules-panel .schedules-bar {
      border-top: 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    }

    .schedules-body {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 12px 14px 14px;
    }

    @keyframes schedules-slide-up {
      from {
        transform: translateY(100%);
      }
      to {
        transform: translateY(0);
      }
    }

    /* The colours alone still tell the mode, the warning and the state. */
    @media (prefers-reduced-motion: reduce) {
      .glow,
      .badge ha-icon,
      .chip--heat,
      .chip--covers,
      .cover-time.pending,
      .schedules-panel,
      .day-mode-list {
        animation: none !important;
      }
      .particles {
        display: none;
      }
    }
  `;
}

if (!customElements.get("homeshift-card")) {
  customElements.define("homeshift-card", HomeShiftCard);
}

export { HomeShiftCard };
