# Entities and services

[← Documentation](../../README.md#documentation) · [Français](../fr/reference.md)

Entity ids do not depend on the language of your Home Assistant: a French installation gets `select.homeshift_day_mode` too, only the names shown are translated. (Ids are given when an entity is first created; an id you renamed is kept.)

Some entities only exist while their feature is set up; they disappear when it is removed.

| Entity | Exists when |
| --- | --- |
| `select.homeshift_day_mode`, `select.homeshift_thermostat_mode` | Always |
| `number.homeshift_override_duration`, `number.homeshift_early_switch` | Always |
| `sensor.homeshift_next_mode`, `sensor.homeshift_next_mode_at` | Always |
| `sensor.homeshift_cover_open_time`, `sensor.homeshift_cover_close_time` | At least one managed cover |
| `binary_sensor.homeshift_covers_left_open` | At least one managed cover |
| `button.homeshift_open_covers`, `button.homeshift_close_covers` | At least one managed cover |
| `sensor.homeshift_covers_inhibited` | At least one cover driven (managed or heat protection) |
| `binary_sensor.homeshift_cover_heat_active` | Heat protection covers and temperature sensor set |
| `sensor.homeshift_auto_start_stop` | At least one climate auto start/stop |

## Day modes

### `select.homeshift_day_mode`

The current [day mode](day-modes.md), set by the calendar or by hand.

- **Options:** `Home`, `Work`, `Remote`, `Away` (`Maison`, `Travail`, `Télétravail`, `Absence` in French)
- **Attributes:** `option_map`, `option_keys`, `current_key`, the key of the current mode whatever the language, and `calendar_error`, `{since: <ISO time>}` while a calendar cannot be read and `null` otherwise

### `select.homeshift_thermostat_mode`

The current thermostat mode, see [Schedules](schedulers.md#thermostat-mode).

- **Options:** `Off`, `Heating`, `Cooling`, `Ventilation`
- **Attributes:** `option_map`, `option_keys`, `current_key`

### `number.homeshift_override_duration`

How long a mode picked by hand is kept before the calendar takes over (minutes, 0 to 1440, step 5, `0` = until the next calendar pass). See [Changing the mode by hand](day-modes.md#changing-the-mode-by-hand).

### `number.homeshift_early_switch`

How long before a timed event its mode starts (minutes, 0 to 480, step 5, `0` = off). See [Early switch](day-modes.md#early-switch).

### `sensor.homeshift_next_mode`

The next day mode. When no change is expected in the next 7 days, the current one.

### `sensor.homeshift_next_mode_at`

When the next mode starts (timestamp), the early switch included.

## Covers

### `sensor.homeshift_cover_open_time`

Today's opening time, `HH:MM`, or `unknown` until computed.

### `sensor.homeshift_cover_close_time`

Today's closing time, `HH:MM`.

- **Attributes:** `sun_elevation`, the configured elevation, and `trigger`: `elevation`, or `sunset` on a day the sun never reached it

### `binary_sensor.homeshift_covers_left_open`

`on` when tonight's close had to leave covers up because of an open window (`device_class: problem`).

- **Attributes:** `covers` (e.g. `["cover.volet_chambre"]`), `window_sensors` (the sensor that kept each one up), `count`, `checked_on`
- Clears when the next day's schedule is computed, not when the window is shut. With [Close When The Window Shuts](covers.md#closing-once-the-window-is-shut), a cover drops off the list once HomeShift closes it.
- Survives a restart.

A notification when covers stay open:

```yaml
automation:
  - alias: Covers left open
    triggers:
      - trigger: state
        entity_id: binary_sensor.homeshift_covers_left_open
        to: "on"
    actions:
      - action: notify.persistent_notification
        data:
          message: >
            Covers not closed tonight:
            {{ state_attr('binary_sensor.homeshift_covers_left_open', 'covers') | join(', ') }}
```

### `binary_sensor.homeshift_cover_heat_active`

`on` while [heat protection](covers.md#heat-protection) conditions are met: inside today's window and the outdoor temperature above the threshold (`device_class: heat`). `unknown` until today's times are computed, or while the temperature sensor is unavailable.

### `button.homeshift_open_covers` / `button.homeshift_close_covers`

Open or close the managed covers now. See [Opening and closing on demand](covers.md#opening-and-closing-on-demand). A failed command is logged; it never makes the buttons unavailable.

### `sensor.homeshift_covers_inhibited`

The number of [paused covers](covers.md#pausing-covers).

- **Attributes:** `covers`, each paused cover with its end (`null` = until resumed), e.g. `{"cover.volet_chambre": "2026-10-12T08:00:00+02:00"}`, and `managed_covers`, every cover that can be paused
- A pause that ends disappears at the next poll (within 5 minutes).

## Climate auto start/stop

### `sensor.homeshift_auto_start_stop`

The number of [climates](climates.md) kept running by their setpoint right now.

- **Attribute** `climates`, one entry per climate:

| Key | Meaning |
| --- | --- |
| `switch` | The auto start/stop switch |
| `name` | Its name, without "Enable auto start/stop" |
| `driven` | Whether HomeShift drives it in the current thermostat mode |
| `comfort` | Whether its setpoint is on the comfort side of the threshold (`null` when not driven) |
| `auto_start_stop` | The switch's actual state (`null` when unavailable) |
| `manual` | The switch differs from what HomeShift set: flipped by hand |
| `setpoint` | The climate's target temperature (`null` when it has none) |
| `threshold` | The threshold of the current thermostat mode (`null` when not driven) |
| `comfort_when` | `above` (heating) or `below` (cooling, ventilation): the side of the threshold that keeps it running |

## Services

### `homeshift.sync_calendar`

Reads the calendars now and updates the day mode if needed (it also runs every 5 minutes).

### `homeshift.refresh_schedulers`

Applies the [scheduler switches](schedulers.md) of the current day and thermostat modes again.

### `homeshift.open_covers` / `homeshift.close_covers`

Same as the buttons above. No field. Does nothing (and logs a warning) without managed covers. Paused covers are left alone.

### `homeshift.inhibit_covers`

[Pauses](covers.md#pausing-covers) covers.

| Field | Required | Description |
| --- | :---: | --- |
| `entity_id` | ✅ | The covers to pause. Only covers HomeShift drives are accepted. |
| `duration` | | How long, e.g. `{"days": 3}` or `"72:00:00"` |
| `until` | | When it ends, e.g. `"2026-10-12 08:00:00"` (Home Assistant's time zone) |

Give `duration` or `until`; with neither, the pause lasts until resumed. Calling it again on a paused cover replaces its end.

```yaml
action: homeshift.inhibit_covers
data:
  entity_id:
    - cover.volet_chambre
  duration:
    days: 3
```

### `homeshift.resume_covers`

Ends pauses early. `entity_id` is optional: without it, every paused cover is resumed.

## Diagnostics

**Download diagnostics**, on the integration's page, dumps the configuration, the coordinator data and today's cover schedule, for a bug report.
