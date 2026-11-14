import { LitElement, html, svg, css, nothing } from "lit";
import { property } from "lit/decorators.js";
import { localize } from "../localize/localize";
import { callService } from "../notify";
import { secondsOfDay } from "../time";
import {
  DAY_MINUTES,
  Schedule,
  Segment,
  SlotValue,
  daySegments,
  formatMinutes,
  scheduleEntities,
  schedulesFor,
  segmentColors,
  sunTimes,
  SunTimes,
} from "./timeline";

const KIND_ICONS: Record<string, string> = {
  heat: "mdi:radiator",
  cool: "mdi:snowflake",
  // A preset alone does not say heating or cooling: heating, as for the exclusion.
  preset: "mdi:radiator",
  on: "mdi:toggle-switch-outline",
  off: "mdi:toggle-switch-off-outline",
  other: "mdi:calendar-clock",
};

/** Schedules sharing a heading: those driving the same room's thermostat. */
interface Room {
  name: string;
  /** Entity the schedules drive, when they drive a single one. */
  entity?: string;
  schedules: Schedule[];
}

/** Whether a timeline heats or cools, for the heating / cooling exclusion. */
function climateSide(kind: string): "heat" | "cool" | undefined {
  if (kind === "cool") return "cool";
  if (kind === "heat" || kind === "preset") return "heat";
  return undefined;
}

/** Switch colour ("r, g, b") of a heating or cooling timeline; others take the card's. */
const SIDE_COLORS: Record<string, string> = {
  heat: "255, 140, 40",
  cool: "61, 155, 233",
};

const CHECK = svg`<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.2 5 8.5l4.5-5" /></svg>`;
const CROSS = svg`<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 3.5l5 5M8.5 3.5l-5 5" /></svg>`;

/** Order of a room's timelines: heating first, then cooling. */
const KIND_ORDER = ["heat", "preset", "cool", "on", "off", "other"];

/**
 * Kind of a timeline, for its icon: cooling wins, then heating, then
 * presets; turning off alone does not tell what the schedule is for.
 */
function rowKind(segments: Segment[]): string {
  const kinds = new Set(segments.map((s) => s.value.kind));
  return (
    ["cool", "heat", "preset", "on", "off"].find((kind) => kinds.has(kind as any)) ??
    "other"
  );
}

/**
 * 24 h timelines of the schedules tagged with one day mode, grouped by
 * room, each with the switch that enables it. The schedules are handed
 * over by the card, which fetches them once for the whole dashboard view.
 */
export class HomeShiftScheduleTimeline extends LitElement {
  @property({ attribute: false }) public hass!: any;
  @property({ attribute: false }) public schedules: Schedule[] = [];
  /** Scheduler tag of the schedules shown: the day mode. */
  @property() public tag = "";
  /** Only the schedules acting on these entities, when there are some. */
  @property({ attribute: false }) public entities: string[] = [];
  private _clock?: ReturnType<typeof setInterval>;

  connectedCallback() {
    super.connectedCallback();
    // Moves the "now" marker along the timelines.
    this._clock = setInterval(() => this.requestUpdate(), 60_000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this._clock);
  }

  protected render() {
    if (!this.hass) return nothing;
    const schedules = schedulesFor(this.schedules, this.tag, this.entities);
    if (!schedules.length) {
      return html`<div class="empty">
        ${localize(this.hass, "schedule.empty", { mode: this.tag })}
      </div>`;
    }
    // The timeslots are times of the server's day, whatever the profile
    // says: the "now" marker follows the server's clock too.
    const zone = this.hass.config?.time_zone || undefined;
    const nowMinutes = Math.floor(secondsOfDay(new Date(), zone) / 60);
    return html`
      ${this._rooms(schedules).map((room) => this._renderRoom(room, nowMinutes))}
      <div class="axis" aria-hidden="true">
        ${[0, 6, 12, 18, 24].map(
          (h) => html`<span style="left: ${(h / 24) * 100}%">${h}h</span>`,
        )}
      </div>
    `;
  }

  /**
   * Schedules grouped by room: those driving the same single entity (e.g.
   * the heating and the cooling of the living room) share a heading; any
   * other schedule is a room of its own, named after itself.
   */
  private _rooms(schedules: Schedule[]): Room[] {
    const rooms = new Map<string, Room>();
    for (const schedule of schedules) {
      const entities = scheduleEntities(schedule, true);
      const entity = entities.length === 1 ? entities[0] : undefined;
      const key = entity ?? schedule.entity_id;
      if (!rooms.has(key)) {
        const name = entity
          ? (this.hass.states[entity]?.attributes?.friendly_name ?? entity)
          : schedule.name;
        rooms.set(key, { name, entity, schedules: [] });
      }
      rooms.get(key)!.schedules.push(schedule);
    }
    for (const room of rooms.values()) {
      room.schedules.sort(
        (a, b) =>
          KIND_ORDER.indexOf(rowKind(daySegments(a, this._sun()))) -
          KIND_ORDER.indexOf(rowKind(daySegments(b, this._sun()))),
      );
    }
    return [...rooms.values()];
  }

  private _renderRoom(room: Room, nowMinutes: number) {
    const measured = room.entity?.startsWith("climate.")
      ? this.hass.states[room.entity]?.attributes?.current_temperature
      : undefined;
    const allDisabled = room.schedules.every((s) => !this._enabled(s));
    return html`
      <div class="room">
        <div class="room-head">
          <span class="room-name ${allDisabled ? "disabled" : ""}">${room.name}</span>
          ${typeof measured === "number"
            ? html`<span class="measured">${this._number(measured)}°</span>`
            : nothing}
        </div>
        ${room.schedules.map((s) => this._renderRow(s, room, nowMinutes))}
      </div>
    `;
  }

  /** Sunrise and sunset, for the timeslots set relative to them. */
  private _sun(): SunTimes {
    // Server time, like the timeslots and the "now" marker.
    return sunTimes(this.hass.states["sun.sun"], this.hass.config?.time_zone || undefined);
  }

  private _enabled(schedule: Schedule): boolean {
    const state = this.hass.states[schedule.entity_id];
    return state ? state.state !== "off" : schedule.enabled;
  }

  /** One schedule: its kind, its timeline and its switch. */
  private _renderRow(schedule: Schedule, room: Room, nowMinutes: number) {
    const segments = daySegments(schedule, this._sun());
    const kind = rowKind(segments);
    const enabled = this._enabled(schedule);
    const side = climateSide(kind);

    return html`
      <div class="row ${enabled ? "" : "disabled"}" title=${schedule.name}>
        <ha-icon class="kind ${kind}" icon=${KIND_ICONS[kind]}></ha-icon>
        <div class="bar" role="img" aria-label=${this._summary(schedule, segments)}>
          ${segments.map((s) => this._renderSegment(s))}
          <div class="now" style="left: ${(nowMinutes / DAY_MINUTES) * 100}%"></div>
        </div>
        <button
          class="switch ${enabled ? "on" : ""}"
          role="switch"
          style=${side ? `--c: ${SIDE_COLORS[side]}` : ""}
          aria-checked=${enabled ? "true" : "false"}
          aria-label=${schedule.name}
          @click=${() => this._toggle(schedule, room, enabled)}
        >
          <span class="knob">${enabled ? CHECK : CROSS}</span>
        </button>
      </div>
    `;
  }

  /**
   * What the timeline shows, for screen readers: the schedule's name, then
   * each segment's range and value ("Travail salon: 00:00 – 07:00 18°, …").
   */
  private _summary(schedule: Schedule, segments: Segment[]): string {
    const parts = segments.map(
      (s) => `${this._range(s)} ${this._label(s.value)}`.trim(),
    );
    return parts.length ? `${schedule.name}: ${parts.join(", ")}` : schedule.name;
  }

  private _range(segment: Segment): string {
    return `${formatMinutes(segment.start)} – ${formatMinutes(segment.end)}`;
  }

  private _renderSegment(segment: Segment) {
    const { background, color } = segmentColors(segment.value);
    const width = ((segment.end - segment.start) / DAY_MINUTES) * 100;
    const range = this._range(segment);
    const label = this._label(segment.value);
    // The card is narrow: a label is written only where it fits, about 2 %
    // of the bar per character ("18°" fits in 10 %, "Confort" needs 16 %).
    const fits = width >= Math.max(10, label.length * 2.2);
    return html`<div
      class="segment"
      style="left: ${(segment.start / DAY_MINUTES) * 100}%; width: ${width}%; background-color: ${background}; color: ${color}"
      title="${range} · ${label}"
    >
      ${fits ? label : nothing}
    </div>`;
  }

  /** A number in the user's format (20.5 / 20,5). */
  private _number(value: number): string {
    const language = this.hass.locale?.language ?? this.hass.language ?? "en";
    return value.toLocaleString(language, { maximumFractionDigits: 1 });
  }

  /** Text of a value, with the temperature in the user's number format (20.5° / 20,5°). */
  private _label(value: SlotValue): string {
    const stateObj = value.entity ? this.hass.states[value.entity] : undefined;
    if (value.temperature != null) return `${this._number(value.temperature)}°`;
    // Presets and HVAC modes as Home Assistant names them ("Confort", "Éteint"...).
    if (value.preset != null) {
      return stateObj && this.hass.formatEntityAttributeValue
        ? this.hass.formatEntityAttributeValue(stateObj, "preset_mode", value.preset)
        : value.preset;
    }
    if (value.hvacMode != null) {
      return stateObj && this.hass.formatEntityState
        ? this.hass.formatEntityState(stateObj, value.hvacMode)
        : value.hvacMode;
    }
    if (value.kind === "on" || value.kind === "off") {
      return localize(this.hass, `schedule.${value.kind}`);
    }
    return value.label;
  }

  /**
   * Turns a schedule on or off. Heating and cooling the same room at once
   * makes no sense: turning one on first turns off the room's enabled
   * schedules of the other side. A refused call is reported as a toast; if
   * the other side cannot be turned off, this one is not turned on.
   */
  private async _toggle(schedule: Schedule, room: Room, enabled: boolean) {
    const call = (service: string, entity_id: string | string[]) =>
      callService(this, this.hass, "schedule.toggle_failed", "switch", service, {
        entity_id,
      });
    if (enabled) {
      await call("turn_off", schedule.entity_id);
      return;
    }
    const side = climateSide(rowKind(daySegments(schedule, this._sun())));
    const opposite = side
      ? room.schedules.filter((s) => {
          const other = climateSide(rowKind(daySegments(s, this._sun())));
          return s !== schedule && other && other !== side && this._enabled(s);
        })
      : [];
    if (opposite.length && !(await call("turn_off", opposite.map((s) => s.entity_id)))) {
      return;
    }
    await call("turn_on", schedule.entity_id);
  }

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .room {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .room-head {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }
    .room-name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 500;
    }
    .room-name.disabled {
      color: var(--secondary-text-color);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .row .bar {
      flex: 1;
    }
    /* A disabled schedule keeps its colours, hatched and dimmed, so it stays
       readable but clearly does not run. */
    .row.disabled .bar {
      opacity: 0.62;
      filter: saturate(0.7);
    }
    .row.disabled .segment {
      background-image: repeating-linear-gradient(
        135deg,
        rgba(0, 0, 0, 0.45) 0 5px,
        transparent 5px 10px
      );
    }
    .kind {
      flex: none;
      display: flex;
      justify-content: center;
      width: 20px;
      --mdc-icon-size: 18px;
      color: var(--secondary-text-color);
      transition: color 0.3s;
    }
    .kind.heat,
    .kind.preset {
      color: #ffa63d;
    }
    .kind.cool {
      color: #6fb4ff;
    }
    .row.disabled .kind {
      color: rgba(220, 235, 240, 0.35);
    }
    .measured {
      flex: none;
      display: flex;
      align-items: center;
      height: 22px;
      padding: 0 9px;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }
    /* 44 x 24 track, 18 px knob centred by flexbox, 3 px from every edge:
       outlined and crossed when off, filled and ticked when on. */
    .switch {
      flex: none;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      width: 44px;
      height: 24px;
      margin: 0;
      padding: 0 3px;
      border: none;
      border-radius: 12px;
      background: transparent;
      box-shadow: inset 0 0 0 1.5px rgba(220, 235, 240, 0.3);
      cursor: pointer;
      transition:
        background 0.25s,
        box-shadow 0.25s;
      --c: var(--m, 3, 169, 244);
    }
    .knob {
      flex: none;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      margin-left: 0;
      border-radius: 50%;
      background: rgba(220, 235, 240, 0.4);
      color: #141c26;
      transition:
        margin-left 0.25s,
        background 0.25s,
        color 0.25s;
    }
    .knob svg {
      display: block;
      width: 10px;
      height: 10px;
      fill: none;
      stroke: currentColor;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .switch.on {
      background: rgb(var(--c));
      box-shadow: none;
    }
    .switch.on .knob {
      margin-left: 20px;
      background: #fff;
      color: rgb(var(--c));
    }
    .switch:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }
    .bar {
      position: relative;
      height: 28px;
      border-radius: 9px;
      background: rgba(0, 0, 0, 0.3);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05);
      overflow: hidden;
      transition:
        opacity 0.3s,
        filter 0.3s;
    }
    .segment {
      position: absolute;
      top: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11.5px;
      font-weight: 600;
      overflow: hidden;
      white-space: nowrap;
      box-shadow: inset -2px 0 0 #121a24;
    }
    .now {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      margin-left: -1px;
      border-radius: 1px;
      background: #fff;
      box-shadow: 0 0 6px rgba(255, 255, 255, 0.8);
    }
    .axis {
      position: relative;
      height: 14px;
      /* Under the bars only: past the kind icon (20 + 8 px) and before the switch (44 + 8 px). */
      margin: -6px 52px 0 28px;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      color: var(--secondary-text-color);
    }
    .axis span {
      position: absolute;
      transform: translateX(-50%);
    }
    .axis span:first-child {
      transform: none;
    }
    .axis span:last-child {
      transform: translateX(-100%);
    }
    .empty {
      padding: 16px 0;
      text-align: center;
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    @media (prefers-reduced-motion: reduce) {
      .switch,
      .knob,
      .bar {
        transition: none;
      }
    }
  `;
}

if (!customElements.get("homeshift-schedule-timeline")) {
  customElements.define("homeshift-schedule-timeline", HomeShiftScheduleTimeline);
}
