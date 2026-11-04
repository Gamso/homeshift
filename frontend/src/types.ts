/** Card configuration, shared by the card and its visual editor. */
export interface HomeShiftCardConfig {
  name?: string;
  day_mode_entity?: string;
  thermostat_mode_entity?: string;
  override_duration_entity?: string;
  early_switch_entity?: string;
  next_mode_entity?: string;
  next_mode_at_entity?: string;
  heat_protection_entity?: string;
  cover_open_time_entity?: string;
  cover_close_time_entity?: string;
  /** Button pressed by the "open now" row (HomeShift >= button platform). */
  open_covers_entity?: string;
  /** Button pressed by the "close now" row. */
  close_covers_entity?: string;
  /** Legacy: when set, the rows call cover.open/close_cover on it instead. */
  cover_entity?: string;
  covers_left_open_entity?: string;
  /** HomeShift's covers_inhibited sensor: the cover automation pause row. */
  covers_inhibited_entity?: string;
  /** HomeShift's auto_start_stop sensor: the climate section. */
  auto_start_stop_entity?: string;
  /**
   * Schedules panel: false hides it. Otherwise it appears on its own once
   * the Scheduler integration holds schedules tagged with a day mode.
   */
  show_schedules?: boolean;
  /** Only the schedules acting on these entities, in the schedules panel. */
  schedule_entities?: string[];
}

export type EntityConfigKey = {
  [K in keyof HomeShiftCardConfig]-?: K extends `${string}_entity` ? K : never;
}[keyof HomeShiftCardConfig];

/**
 * Every entity option, in editor order, with the domains its picker offers
 * and the entity the HomeShift integration creates by default ("" = none).
 * The editor is generated from this table so it cannot drift from the
 * config keys the card reads.
 */
export const ENTITY_FIELDS: readonly {
  key: EntityConfigKey;
  domains: string[];
  default: string;
}[] = [
  {
    key: "day_mode_entity",
    domains: ["select", "input_select"],
    default: "select.homeshift_day_mode",
  },
  {
    key: "thermostat_mode_entity",
    domains: ["select", "input_select"],
    default: "select.homeshift_thermostat_mode",
  },
  {
    key: "override_duration_entity",
    domains: ["number", "input_number"],
    default: "number.homeshift_override_duration",
  },
  {
    key: "early_switch_entity",
    domains: ["number", "input_number"],
    default: "number.homeshift_early_switch",
  },
  {
    key: "next_mode_entity",
    domains: ["sensor"],
    default: "sensor.homeshift_next_mode",
  },
  {
    key: "next_mode_at_entity",
    domains: ["sensor"],
    default: "sensor.homeshift_next_mode_at",
  },
  {
    key: "heat_protection_entity",
    domains: ["binary_sensor"],
    default: "binary_sensor.homeshift_cover_heat_active",
  },
  {
    key: "cover_open_time_entity",
    domains: ["sensor"],
    default: "sensor.homeshift_cover_open_time",
  },
  {
    key: "cover_close_time_entity",
    domains: ["sensor"],
    default: "sensor.homeshift_cover_close_time",
  },
  {
    key: "open_covers_entity",
    domains: ["button"],
    default: "button.homeshift_open_covers",
  },
  {
    key: "close_covers_entity",
    domains: ["button"],
    default: "button.homeshift_close_covers",
  },
  {
    key: "cover_entity",
    domains: ["cover"],
    default: "",
  },
  {
    key: "covers_left_open_entity",
    domains: ["binary_sensor"],
    default: "binary_sensor.homeshift_covers_left_open",
  },
  {
    key: "covers_inhibited_entity",
    domains: ["sensor"],
    default: "sensor.homeshift_covers_inhibited",
  },
  {
    key: "auto_start_stop_entity",
    domains: ["sensor"],
    default: "sensor.homeshift_auto_start_stop",
  },
];
