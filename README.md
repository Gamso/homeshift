# HomeShift — Home Assistant Custom Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Automatic day-mode and thermostat-mode management for Home Assistant, driven by your calendar.

---

## Table of Contents

- [HomeShift — Home Assistant Custom Integration](#homeshift--home-assistant-custom-integration)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [HACS (Recommended)](#hacs-recommended)
  - [✨ Overview](#-overview)
    - [How It Works](#how-it-works)
  - [✅ Requirements](#-requirements)
  - [⚙️ Quick Setup](#️-quick-setup)
  - [📊 Entities](#-entities)
    - [`select.homeshift_day_mode`](#selecthomeshift_day_mode)
    - [`select.homeshift_thermostat_mode`](#selecthomeshift_thermostat_mode)
    - [`number.homeshift_override_duration`](#numberhomeshift_override_duration)
    - [`number.homeshift_early_switch`](#numberhomeshift_early_switch)
    - [`sensor.homeshift_next_mode`](#sensorhomeshift_next_mode)
    - [`sensor.homeshift_next_mode_at`](#sensorhomeshift_next_mode_at)
    - [`sensor.homeshift_cover_open_time`](#sensorhomeshift_cover_open_time)
    - [`sensor.homeshift_cover_close_time`](#sensorhomeshift_cover_close_time)
    - [`binary_sensor.homeshift_covers_left_open`](#binary_sensorhomeshift_covers_left_open)
    - [`binary_sensor.homeshift_cover_heat_active`](#binary_sensorhomeshift_cover_heat_active)
    - [`button.homeshift_open_covers` / `button.homeshift_close_covers`](#buttonhomeshift_open_covers--buttonhomeshift_close_covers)
    - [`sensor.homeshift_covers_inhibited`](#sensorhomeshift_covers_inhibited)
  - [🛠️ Services](#️-services)
    - [`homeshift.refresh_schedulers`](#homeshiftrefresh_schedulers)
    - [`homeshift.sync_calendar`](#homeshiftsync_calendar)
    - [`homeshift.open_covers` / `homeshift.close_covers`](#homeshiftopen_covers--homeshiftclose_covers)
    - [`homeshift.inhibit_covers`](#homeshiftinhibit_covers)
    - [`homeshift.resume_covers`](#homeshiftresume_covers)
  - [⚙️ Configuration Parameters](#️-configuration-parameters)
  - [🧠 Detection Logic](#-detection-logic)
    - [Half-Day Events](#half-day-events)
    - [Early Switch](#early-switch)
    - [When a Calendar Cannot Be Read](#when-a-calendar-cannot-be-read)
  - [🗓️ Scheduler Integration](#️-scheduler-integration)
    - [Thermostat Tags](#thermostat-tags)
  - [🗓️ Daily Cover Schedule](#️-daily-cover-schedule)
    - [When the Covers Close](#when-the-covers-close)
    - [Individual Covers](#individual-covers)
    - [Opening and Closing on Demand](#opening-and-closing-on-demand)
  - [☀️ Cover Heat Protection](#️-cover-heat-protection)
    - [Reactive Close](#reactive-close)
    - [Proactive Forecast-Based Close](#proactive-forecast-based-close)
    - [State Persistence](#state-persistence)
  - [🧩 Feature Support](#-feature-support)
  - [📄 License](#-license)

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three-dot menu → **Custom repositories**
4. Add `https://github.com/Gamso/homeshift` with category **Integration**
5. Search for **HomeShift** and install it
6. Restart Home Assistant

---

## ✨ Overview

HomeShift is a custom Home Assistant integration that automatically manages **day modes** (e.g. Home, Work, Remote, Away) and **thermostat modes** (e.g. Heating, Cooling, Off) based on your calendar events, weekends, and public holidays.

Every 5 minutes (a fixed interval, plus precise timers for the changes it can predict), it reads your calendar, picks the right day mode, and turns the matching scheduler switches on or off — so your home adapts automatically without any manual intervention.

### How It Works

1. Reads the active event from your work/schedule calendar
2. Checks your public holiday calendar
3. Determines the day mode based on a configurable event → mode mapping
4. Turns on the scheduler switches for the active mode, and turns off all others

---

## ✅ Requirements

- **Home Assistant 2026.9** or newer
- A **calendar** entity containing your work or schedule events
- A **calendar** entity for public holidays
- The [Scheduler integration](https://github.com/nielsfaber/scheduler-component) to automate scheduler switches

> **Scheduler tags (required for thermostat integration):** When using the Scheduler integration alongside `thermostat_mode`, each scheduler switch that controls heating or cooling **must have the matching thermostat tag** (e.g. `Heating`, `Cooling`). Schedulers without any thermostat tag are treated as day-mode-only and are never force-disabled by the thermostat logic. See the [Thermostat Tags](#thermostat-tags) section for details.

---

## ⚙️ Quick Setup

1. Go to **Settings → Devices & Services → Add Integration → HomeShift**
2. Select your work calendar entity and your holiday calendar entity (both required)
3. Optionally rename the day modes and thermostat modes, assign schedulers, and set up the covers
4. Save — HomeShift starts working immediately

Once set up, HomeShift will:
- Read your calendar every 5 minutes
- Automatically update `select.homeshift_day_mode`
- Turn the right scheduler switches on and off

---

## 📊 Entities

Entity ids are fixed and do not depend on the language of your Home Assistant instance: a French installation gets `select.homeshift_day_mode` too, only the displayed names are translated. (They are given when an entity is first created; an id you renamed yourself is kept.)

### `select.homeshift_day_mode`
Shows and controls the current day mode. HomeShift updates it automatically based on your calendar, but you can also change it manually at any time.

- **Type:** Select
- **Default options:** `Home`, `Work`, `Remote`, `Away` (`Maison`, `Travail`, `Télétravail`, `Absence` on a French instance)
- **Writable:** Yes — a manual change can be protected from auto-updates using the override duration
- **Attributes:** `option_map`, `option_keys`, `current_key` — the key of the current mode, the same whatever the language

### `select.homeshift_thermostat_mode`
Shows and controls the current thermostat mode.

- **Type:** Select
- **Default options:** `Off`, `Heating`, `Cooling`, `Ventilation`
- **Writable:** Yes

### `number.homeshift_override_duration`
When you manually change the day mode, this setting defines how long (in minutes) HomeShift waits before resuming automatic updates. Set to `0` to always allow automatic updates.

- **Type:** Number (minutes, 0–1440, step 5)
- **Default:** `0` (disabled)
- A running override survives a Home Assistant restart.

---

### `number.homeshift_early_switch`
Pre-activates an upcoming timed calendar event before it officially starts. When set, HomeShift switches to the correct day mode up to X minutes before the event start.

- **Type:** Number (minutes, 0–480, step 5)
- **Default:** `0` (disabled)
- **Only applies to timed events** — all-day events are always ignored.

**Example:** You have a *Remote work* event from 14:00 to 18:00 and `early_switch = 120`. HomeShift will switch to `Remote working` mode at **12:00**, giving your heating schedule 2 hours to warm the house before you start working.

The `sensor.homeshift_next_mode_at` and `sensor.homeshift_next_mode` sensors reflect this anticipated switch time, so you can display it on a dashboard.

---

### `sensor.homeshift_next_mode`
Shows the predicted next day mode that HomeShift will switch to.

- **Type:** Sensor (text)
- **Value:** Display name of the predicted next mode (e.g. `Remote`). When no change is expected in the next 7 days, shows the current day mode.

### `sensor.homeshift_next_mode_at`
Shows when the next automatic mode change is expected to occur (taking early_switch into account for timed events).

- **Type:** Sensor (timestamp)
- **Unit:** ISO 8601 datetime

### `sensor.homeshift_cover_open_time`
Shows the cover opening time computed for today by the Daily Cover Schedule feature.

- **Type:** Sensor (text)
- **Value:** `HH:MM` string (e.g. `07:45`), or `unknown` if not configured or has not run yet.
- **Only registered** when at least one cover is listed under **Individual Covers**.

### `sensor.homeshift_cover_close_time`
Shows the estimated daily cover closing time for today, computed by the Daily Cover Schedule feature from the [configured sun elevation](#when-the-covers-close).

- **Type:** Sensor (text)
- **Value:** `HH:MM` string (e.g. `21:40`), or `unknown` if not configured or not yet computed.
- **Attributes:**
  - `sun_elevation` — the configured elevation the time was computed from
  - `trigger` — `elevation` normally, `sunset` on a day the sun never reached it and the fallback stepped in
- **Only registered** when at least one cover is listed under **Individual Covers**.

### `binary_sensor.homeshift_covers_left_open`
Warns that tonight's close had to leave covers up, and names them.

- **Type:** Binary sensor (`device_class: problem`)
- **Value:** `on` when at least one cover was skipped by the evening close, `off` otherwise.
- **Attributes:**
  - `covers` — the entity ids left open, e.g. `["cover.volet_chambre"]`
  - `window_sensors` — the sensor that blocked each one, e.g. `{"cover.volet_chambre": "binary_sensor.fenetre_chambre"}`
  - `count`, `checked_on` — how many, and the day the close ran
- **Clears** when the next calendar day's schedule is computed, **not** when the window is closed — the cover stays up either way until someone acts on it.
- **Only registered** when at least one cover is listed under **Individual Covers**.
- **Survives a restart:** the list is persisted with the rest of the day's cover state.

A notification automation can read the list straight out of the attributes:

```yaml
automation:
  - alias: Volets restés ouverts
    triggers:
      - trigger: state
        entity_id: binary_sensor.homeshift_covers_left_open
        to: "on"
    actions:
      - action: notify.persistent_notification
        data:
          message: >
            Volets non fermés ce soir :
            {{ state_attr('binary_sensor.homeshift_covers_left_open', 'covers') | join(', ') }}
```

### `binary_sensor.homeshift_cover_heat_active`
`on` while the heat protection conditions are met: inside today's heat protection window and the outdoor temperature above **Temperature Threshold**.

- **Type:** Binary sensor (`device_class: heat`)
- **Value:** `unknown` until the Daily Cover Schedule has computed today's times, or while the temperature sensor is unavailable.
- **Only registered** when **Cover Entities** and **Temperature Sensor** are both configured.

### `button.homeshift_open_covers` / `button.homeshift_close_covers`
Open or close the covers of the daily schedule right now, whatever the time and the day mode. See [Opening and Closing on Demand](#opening-and-closing-on-demand).

- **Type:** Button (icons `mdi:window-shutter-open` / `mdi:window-shutter`)
- **Only registered** when at least one cover is listed under **Individual Covers**.
- **Always available:** a failed cover command is logged, it never turns the buttons (or any other HomeShift entity) unavailable.

### `sensor.homeshift_covers_inhibited`
Lists the covers taken out of the automation by [`homeshift.inhibit_covers`](#homeshiftinhibit_covers).

- **Type:** Sensor
- **Value:** how many covers are currently inhibited (`0` when none).
- **Attributes:**
  - `covers` — each inhibited cover with the end of its inhibition, e.g. `{"cover.volet_chambre": "2026-10-12T08:00:00+02:00", "cover.volet_bureau": null}` (`null`: until resumed)
  - `managed_covers` — every cover HomeShift drives, i.e. every cover that can be inhibited
- **Only registered** when HomeShift drives at least one cover (Individual Covers or heat protection).
- An inhibition that runs out disappears at the next poll (within 5 minutes).

---

## 🛠️ Services

### `homeshift.refresh_schedulers`
Immediately refreshes the scheduler switches based on the current day mode and thermostat mode. Useful after manually changing a mode.

### `homeshift.sync_calendar`
Manually triggers a calendar check and updates `select.homeshift_day_mode` if needed. This is also called automatically at regular intervals.

### `homeshift.open_covers` / `homeshift.close_covers`
Same as pressing `button.homeshift_open_covers` / `button.homeshift_close_covers`: open or close the covers of the daily schedule now. No field. Does nothing (and logs a warning) when no cover is listed under **Individual Covers**. Inhibited covers are left where they are.

### `homeshift.inhibit_covers`
Temporarily takes one or more covers out of the automation — e.g. to keep a bedroom dark for a few days. An inhibited cover receives neither the daily open nor the evening close, heat protection leaves it alone, and the open/close-now buttons and services skip it.

| Field | Required | Description |
| --- | :---: | --- |
| `entity_id` | ✅ | The covers to leave alone. Only covers HomeShift drives are accepted. |
| `duration` | | How long, e.g. `{"days": 3}` or `"72:00:00"`. |
| `until` | | When it ends, e.g. `"2026-10-12 08:00:00"` (read in Home Assistant's time zone). |

Give either `duration` or `until`; with neither, the covers stay inhibited until [`homeshift.resume_covers`](#homeshiftresume_covers). Calling it again on an inhibited cover replaces its end. Inhibitions survive a restart.

```yaml
action: homeshift.inhibit_covers
data:
  entity_id:
    - cover.volet_chambre
  duration:
    days: 3
```

Inhibiting or resuming does not move a cover by itself. When an inhibition ends, the cover simply takes part in the next scheduled action — a missed morning open is not replayed in the afternoon. Heat protection is the exception: it stays armed, so a cover released on a hot afternoon can still be closed by it. A My position button configured for heat protection moves all its covers at once, so it is not pressed while any of them is inhibited.

### `homeshift.resume_covers`
Hands inhibited covers back to the automation before their end. `entity_id` is optional: without it, every inhibited cover is resumed.

---

## ⚙️ Configuration Parameters

All parameters can be changed at any time via **Settings → Devices & Services → HomeShift → Configure**.

The dialog opens on a menu: **Calendars**, **Day modes**, **Schedulers** and **Covers**, the last one a sub-menu grouping **Managed covers** (the [Individual Covers](#individual-covers) list), **Opening and closing times** (the [Daily Cover Schedule](#️-daily-cover-schedule)) and **Heat protection**. Each entry shows a one-line summary of its current settings. Saving a page brings you back to its menu; nothing is stored until **Save configuration**, and the menu lists the sections changed so far, since closing the dialog with ✕ discards them.

| Parameter                 | Default                         | Description                                                   |
| ------------------------- | ------------------------------- | ------------------------------------------------------------- |
| **Work Calendar**         | —                               | Calendar entity containing your work/schedule events          |
| **Holiday Calendar**      | —                               | Calendar entity for public holidays (required)                |
| **Day Mode Display Names** | `Home, Work, Remote, Away`     | Display name of each of the four day modes (keys `home`, `work`, `remote`, `away`). The modes themselves are fixed: they can be renamed, not added or removed |
| **Thermostat Display Names** | `Off, Heating, Cooling, Ventilation` | Display name of each thermostat mode (keys `off`, `heating`, `cooling`, `ventilation`); also the scheduler tags, see [Thermostat Tags](#thermostat-tags) |
| **Schedulers**            | —                               | Scheduler switches per day mode, see [Scheduler Integration](#️-scheduler-integration) |
| **Override Duration**     | `0` (disabled)                  | Minutes to block automatic updates after a manual mode change (also adjustable from `number.homeshift_override_duration`) |
| **Early Switch**          | `0` (disabled)                  | Minutes to pre-activate a timed event before its start (also adjustable from `number.homeshift_early_switch`) |
| **Default Mode**          | `Work`                          | Mode used on regular weekdays with no calendar event          |
| **Weekend Mode**          | `Home`                          | Mode used on Saturdays and Sundays                            |
| **Holiday Mode**          | `Home`                          | Mode used on public holidays                                  |
| **Event Mode Map**        | `Vacation:home, Remote:remote`  | Maps calendar event keywords to day mode keys (`Vacances:home, Télétravail:remote` on a French instance); matched case-insensitively inside the event title |
| **Away Mode**             | `Away`                          | When *you* select this mode, automatic updates are paused until you leave it |
| **Cover Entities**        | —                               | Cover entities to close when it is too hot (optional; requires Individual Covers below to be configured too) |
| **Temperature Sensor**    | —                               | Sensor providing the outdoor temperature                      |
| **Temperature Threshold** | `30 °C`                         | Temperature above which covers close reactively (fallback for days the forecast misses) |
| **Cover Action**          | `close_cover`                   | Service called when heat protection triggers: `close_cover` or `stop_cover` |
| **My Position Button**    | —                               | Button entity to press instead of a cover service (e.g. Somfy RTS "My" position) |
| **Weather Entity**        | —                               | Weather entity with daily forecasts, used for the proactive close (optional) |
| **Forecast Threshold**    | `28 °C`                         | Forecast daily high above which covers close proactively      |
| **Individual Covers**     | —                               | The covers opened and closed daily, added one at a time, each with an optional window sensor and an optional My position button (separate from Cover Entities above); Cover Heat Protection's active window is derived from this schedule |
| **Open Time — *(per day mode)*** | `08:30`                  | One field per day mode: `sunrise`, `skip`, or a custom `HH:MM` value |
| **Earliest Open Time**    | `07:00`                         | Floor time used when a day mode's Open Time is `sunrise`, and start of heat protection on a `skip` day when sunrise is unknown |
| **Sun Elevation At Closing** | `-2°`                        | Covers close when the descending sun reaches this many degrees above the horizon, every day, for every mode — the same scale as `{{ state_attr('sun.sun', 'elevation') }}`. `0°` is sunset, negative is below the horizon |

---

## 🧠 Detection Logic

Each time HomeShift refreshes, it looks at today's active calendar event and determines the day mode using this priority order:

| Priority | Condition                                                                 | Resulting mode                 |
| -------- | ------------------------------------------------------------------------- | ------------------------------ |
| 1        | Active calendar event matches the event mode map                          | Mapped mode (e.g. `Remote`)    |
| 2        | A timed event starts within `early_switch` minutes and it matches the map | Mapped mode (anticipated)      |
| 3        | Today is Saturday or Sunday                                               | **Weekend mode**               |
| 4        | Today is a public holiday                                                 | **Holiday mode**               |
| 5        | No special condition                                                      | **Default mode** (e.g. `Work`) |

> **Note:** If **you** select the **Away mode** yourself, all automatic updates are paused until you change it manually — that is the point of the mode.
>
> A calendar event mapped to the Away mode does **not** pause anything: it sets the mode like any other event, and the mode moves on normally once the event ends. Otherwise a single mapped event would freeze the integration for good.

### When a Calendar Cannot Be Read

A work or holiday calendar that is missing, `unavailable` or `unknown` (a CalDAV or Google outage, an integration still loading at startup) says nothing about today, so HomeShift does **not** read it as "no event": it keeps the current day mode, logs one warning when the outage starts and one line when it ends, and resumes normal detection as soon as the calendar answers. A remote-work day does not flip to *Work* and back, and an absence set by a calendar event is not cancelled.

The covers do not wait for the calendar: the Daily Cover Schedule and heat protection keep running, with today's times computed from the mode kept so far, and computed again once the calendar answers.

### Half-Day Events

If a calendar event covers only the morning or only the afternoon, HomeShift applies the corresponding mode only during that half of the day, then reverts to the default mode for the other half.

### Early Switch

The `number.homeshift_early_switch` entity lets you anticipate timed calendar events. When the current time is within the early-switch window before a timed event, HomeShift pre-activates the corresponding mode.

```
Calendar event:  Remote working  14:00 ──────────── 18:00
early_switch = 120 min
                             ↑
                          12:00  ← HomeShift switches to Remote working here
```

**Key rules:**
- Only applies to **timed events** (events with a specific start/end time). All-day events (e.g. public holidays) are never pre-activated.
- The `sensor.homeshift_next_mode` and `sensor.homeshift_next_mode_at` sensors reflect the anticipated switch time, not the original event start.
- Setting `early_switch` to `0` disables the feature entirely.

---

## 🗓️ Scheduler Integration

HomeShift can automatically turn scheduler switches on and off based on the current day mode.

In the integration settings, you can assign one or more switch entities to each day mode. When the day mode changes:
- The switches for the **active mode** are turned **on**
- The switches for **all other modes** are turned **off**

This lets you, for example, run different heating schedules depending on whether you're working from home or at the office — without any automation to write.

The assignments are stored per mode **key** (`home`, `work`, ...), so renaming a mode or changing the language of Home Assistant keeps them. A switch that fails to respond (deleted, Scheduler integration unloaded) is reported in the log and does not stop the other switches or the mode change.

> **Upgrading from 1.9.x:** schedulers used to be stored per display name, and on a French instance configured without opening *Mode Mapping* they were stored under the English names, so no scheduler was ever turned on. The entry migration re-keys them by mode key and repairs that case; a name that matches no mode is kept as is and logged.

### Thermostat Tags

When you also use `select.homeshift_thermostat_mode`, HomeShift needs to know which scheduler switches control heating or cooling so it can disable them automatically when the thermostat is off.

To make this work, each scheduler switch that is linked to a specific thermostat mode **must have the corresponding thermostat mode name set as a tag** in the Scheduler card.

**Example:**

Suppose your thermostat modes are `Heating` and `Cooling`. You create the following schedulers:

| Scheduler switch                 | Tags       | Purpose                                   |
| -------------------------------- | ---------- | ----------------------------------------- |
| `switch.schedule_home_heating`   | `Heating`  | Heating schedule when you're at home      |
| `switch.schedule_work_heating`   | `Heating`  | Heating schedule when you're at work      |
| `switch.schedule_home_cooling`   | `Cooling`  | Cooling schedule when you're at home      |
| `switch.schedule_presence_light` | *(no tag)* | Lighting schedule, not thermostat-related |

When `select.homeshift_thermostat_mode` is set to **Off**, HomeShift will force-disable all switches tagged with `Heating` or `Cooling`, regardless of the current day mode. Switches without any thermostat tag (like `switch.schedule_presence_light`) are left untouched.

> **How to add a tag in the Scheduler card:** Open the Scheduler card → edit a schedule → scroll to *Tags* → add the thermostat mode name exactly as defined in your thermostat mode map (e.g. `Heating`, `Cooling`).

---

## 🗓️ Daily Cover Schedule

HomeShift can natively open and close covers every day, without depending on any Scheduler-integration entity. The covers it drives are listed under [Individual Covers](#individual-covers) — one entry per cover, a whole-house cover group counting as one — while this section sets the times. That list is separate from Cover Heat Protection's **Cover Entities**, so a south-facing cover can stay under heat-protection's control while the rest follow the daily open/close schedule below. [Cover Heat Protection](#️-cover-heat-protection) derives its active window from the times computed here, so configure both.

Once per day, shortly after midnight, HomeShift computes:
- **Open time** — resolved per day mode. Each configured day mode has its own **Open Time** field, set to one of:
  - `sunrise` — sunrise, floored at **Earliest Open Time** (e.g. never before `07:00`)
  - `skip` — no automatic opening for that mode (covers stay as they are). Heat protection still runs that day, see [Cover Heat Protection](#️-cover-heat-protection)
  - a custom `HH:MM` value — a fixed clock time
  
  Day modes sharing the same value effectively form a batch (e.g. both `Work` and `Remote` set to `sunrise`). A day mode with no value configured falls back to `08:30`. There's no separate "skip modes" list — set a mode's Open Time to `skip` directly.
- **Close time** — when the setting sun reaches the configured elevation, always, for every day mode (closing is not mode-dependent): see below.

If the day mode changes before the covers opened — an all-day calendar event that the calendar entity only drops or shows a few minutes after midnight, or a mode picked by hand in the morning — the open time is computed again for the new mode. Once the covers opened, a later change (a half-day event in the afternoon) leaves the day's times as they are.

A one-shot timer fires the open/close action at the exact scheduled minute; the periodic coordinator poll (every 5 minutes) acts as a fallback in case the timer is missed (e.g. a HA restart). Each action fires at most once per calendar day. A command that fails (a cover integration timing out, an entity removed) is logged as a warning and sent again at the next poll; it never makes the HomeShift entities unavailable.

**`sensor.homeshift_cover_open_time`** and **`sensor.homeshift_cover_close_time`** reflect today's computed times, so you can display them on your dashboard.

### When the Covers Close

The covers close when the descending sun reaches **Sun Elevation At Closing** degrees above the horizon — the value you would read from `{{ state_attr('sun.sun', 'elevation') }}`, on the same scale. You are setting a **light level**, not a delay:

| Elevation | Roughly | Light |
| --------- | ------- | ----- |
| `+2°`     | Sunset − ~15 min | The sun is still up |
| `0°`      | Sunset  | The sun touches the horizon |
| `-2°` *(default)* | Sunset + ~10 min | Dusk, still easy to see outside |
| `-4°`     | Sunset + ~20-25 min | Room is dark |
| `-6°`     | Sunset + ~35-40 min | End of civil twilight, artificial light needed |

The "roughly" column is a mid-latitude approximation: the delay an elevation works out to shifts a little with latitude and season, which is the point — the light level does not.

Degrees say nothing about when your covers will actually move, so the *Daily Cover Schedule* form turns the value into tonight's time, computed from your own location:

```
At -2°, that is 21:41 tonight.
```

`-2°` is the default because it is where the retired "sunset + 10 minutes" setting used to land, at every season. Pick `-4°` to wait until the room is genuinely dark (about a quarter of an hour later), or a positive value to close before the sun is down.

The form refuses an elevation the sun never reaches at your location — a positive value that the midwinter sun stays below, or any value above the polar circle in June. At mid-latitude nothing in the range can be refused: the sun sweeps all of it every day of the year. Should it become unreachable anyway (a home that moved, an entry restored elsewhere), the covers close at plain sunset rather than staying up all night:

```
WARNING ... Daily cover schedule: the sun never reaches 8.0° on 2026-06-21 — closing at sunset instead
```

> **Upgrading from 1.7.x:** the evening close used to be "sunset ± N minutes". That setting is gone; the entry migration converts your offset into the elevation it was landing on, so the covers keep moving at the time they moved before. The conversion is logged.

### Individual Covers

The covers driven by the daily schedule are added **one at a time** from *Covers → Managed covers*: pick the cover, and optionally a **window opening sensor** (does that window stand open?) and a **My position button** (how should this cover close?). **Edit a cover** changes the sensor or the button of a cover already in the list (clear a field to remove it); adding a cover that is already in the list does the same instead of duplicating it. A cover group is a cover entity like any other, so driving the whole house through one group is simply a single entry.

The window sensor changes one thing: **the evening close skips a cover whose window is reported open.** Rather than closing a cover over an open window, HomeShift leaves it alone and logs a warning:

```
WARNING ... Daily cover schedule: not closing cover 'cover.volet_chambre' — window sensor 'binary_sensor.fenetre_chambre' reports the window open
```

#### My Position Instead of a Full Close

Some covers shouldn't come all the way down in the evening. Give such a cover a **My position button** — the button entity that sends a Somfy RTS (or similar) cover to its recorded favourite position — and the evening close presses that button instead of sending `close_cover` to it:

```
INFO ... Daily cover schedule: pressing My position button 'button.my_salon' for cover 'cover.volet_salon' (close_time=21:40)
```

- The cover is held back from the bulk `close_cover` — it only ever receives its button press.
- An open window still wins: a blocked cover gets neither a close nor a press.
- The **morning open is unchanged** — the My position only changes how a cover closes.
- This is per-cover, and independent of Cover Heat Protection's own **My Position Button** setting.

Details worth knowing:
- **The morning open is never skipped** — an open window is only a reason not to close.
- **A skipped cover is not retried later that night.** The day's close is marked done once it runs; the warning is the signal to close that cover by hand if you want it closed.
- **A sensor that is missing or `unavailable` closes the cover as usual**, with a warning — an unavailable sensor can't establish that the window is open.
- **A cover reached through a group is not protected.** HomeShift sends the close to the entity ids you configured and does not look inside a group, so a cover that should keep its own window sensor or My position must be listed here individually (and dropped from the group).
- Covers without a window sensor behave exactly as before.

### Opening and Closing on Demand

The **Open covers** and **Close covers** buttons (`button.homeshift_open_covers`, `button.homeshift_close_covers`), and the matching `homeshift.open_covers` / `homeshift.close_covers` services, send the daily schedule's own commands at any time — the HomeShift card uses them when you click the opening or closing time.

- **Open** sends `open_cover` to every cover of the list, even on a `skip` day.
- **Close** follows the evening close's rules: a cover whose window sensor reports the window open is left up (with a warning in the log), a cover with a My position button gets a press of that button instead of `close_cover`.
- **The schedule is not changed.** A manual action does not count as today's scheduled open or close: the scheduled action still runs at its time. Opening by hand at 07:00 before an 08:30 opening is harmless (the 08:30 command finds the covers open); closing by hand in the morning does not cancel that day's opening. The `covers_left_open` warning also stays tied to the scheduled evening close.
- A failed command is logged as a warning, like the scheduled ones.

> **Migrating from Scheduler-integration volet entities:** if you previously used two Scheduler entities (a fixed/sunrise-based "open" and a sunset-offset "close") purely to drive covers, you can disable/delete them once Daily Cover Schedule is configured with the same times — HomeShift no longer needs the Scheduler integration for covers at all.

---

## ☀️ Cover Heat Protection

HomeShift can automatically close a cover to prevent heat build-up — without requiring any separate automation, and without a separately configured time window. Once closed by this automation, the cover stays closed for the rest of the day; it never reopens itself. It's touched again either by the next day's normal open, or by Daily Cover Schedule's own unconditional evening close.

**Cover Heat Protection requires [Daily Cover Schedule](#️-daily-cover-schedule) to be configured.** Its active window isn't set independently — it runs from today's opening time to today's closing time, the times Daily Cover Schedule already computes every day. On a `skip` day (no automatic opening, typically *Away*), the window starts at the sunrise-based time instead (sunrise, floored at **Earliest Open Time**): `skip` suppresses the opening, never the protection — that is precisely the day nobody is home to close the cover by hand. This also means: if it's already hot right when the cover would normally open for the day, heat protection can apply the closed/protected position immediately instead of opening it and closing it again moments later.

### Reactive Close

Each time the coordinator runs **and** whenever the temperature sensor value changes, HomeShift checks: if the cover hasn't already been closed by this automation today, and the current time is within today's heat protection window, and the outdoor temperature exceeds **Temperature Threshold**, it applies the configured **Cover Action**: `close_cover` (default), `stop_cover` (interrupts movement mid-travel — useful for Somfy RTS covers), or presses the **My Position Button** if one is configured (sends the cover to its pre-recorded favourite position).

This fires at most once per day — once closed, HomeShift leaves the cover alone regardless of what the temperature does afterward. Nothing is sent when every protected cover already reads `closed` (a `stop_cover` or a My press would only move a closed cover up), and a command that fails is retried at the next check instead of being counted as done.

### Proactive Forecast-Based Close

If a **Weather Entity** (with daily forecasts) is configured, HomeShift also checks — once per day, at the start of today's heat protection window — whether today's forecast high exceeds **Forecast Threshold**. If it does, the cover closes immediately (or skips opening in the first place, if this runs before/at the same moment Daily Cover Schedule opens it), ahead of the outdoor sensor actually crossing the reactive threshold.

The reactive close above still runs during the rest of the window as a fallback, in case the forecast lookup fails or under-predicts the day.

Leave **Weather Entity** unset to disable the proactive close entirely; behavior then falls back to the reactive close only.

### State Persistence

Whether the cover has already been closed by this automation today, and when the forecast was last checked, are persisted to storage, so a Home Assistant restart mid-day doesn't lose track of the day's state. The same storage also tracks whether today's Daily Cover Schedule open/close actions have already run, for the same reason. The day mode, the thermostat mode and a running manual override are persisted by the coordinator.

Both stores are deleted when the integration is removed. **Download diagnostics** (on the integration's page) dumps the configuration, the coordinator data and today's cover schedule, for a bug report.

---

## 🧩 Feature Support

| Feature                                    | Status | Notes                                                              |
| ------------------------------------------- | :----: | -------------------------------------------------------------------|
| Calendar-driven day mode                    |   ✅   | See [Detection Logic](#-detection-logic)                           |
| Thermostat mode + scheduler tags            |   ✅   | See [Thermostat Tags](#thermostat-tags)                            |
| Half-day event support                      |   ✅   | See [Half-Day Events](#half-day-events)                            |
| Early switch (pre-activation)               |   ✅   | See [Early Switch](#early-switch)                                  |
| Manual override with timeout                |   ✅   | `number.homeshift_override_duration`                                         |
| Native daily cover open/close (no Scheduler entity needed) | ✅ | See [Daily Cover Schedule](#️-daily-cover-schedule)                |
| Daily cover schedule state survives HA restart |  ✅  | Persisted alongside the heat-protection cover state                |
| Evening close driven by the sun's elevation | ✅ | See [When the Covers Close](#when-the-covers-close) |
| Skip the evening close when a window is open |  ✅  | See [Individual Covers](#individual-covers) |
| Warning entity listing the covers left open |  ✅  | `binary_sensor.homeshift_covers_left_open` |
| Per-cover My position instead of a full close |  ✅  | See [Individual Covers](#individual-covers) |
| Temporarily inhibit the automation of chosen covers | ✅ | [`homeshift.inhibit_covers`](#homeshiftinhibit_covers), `sensor.homeshift_covers_inhibited` |
| Open / close the covers on demand           |   ✅   | See [Opening and Closing on Demand](#opening-and-closing-on-demand) |
| Cover reactive heat close                   |   ✅   | See [Reactive Close](#reactive-close); active window derived from Daily Cover Schedule; never reopens itself |
| Cover proactive forecast-based close        |   ✅   | See [Proactive Forecast-Based Close](#proactive-forecast-based-close) |
| Cover automation state survives HA restart  |   ✅   | See [State Persistence](#state-persistence)                        |
| Day-mode/thermostat-mode state survives HA restart |  ✅  | Restored from storage at startup, with a running manual override |
| Calendar outage keeps the current mode      |   ✅   | See [When a Calendar Cannot Be Read](#when-a-calendar-cannot-be-read) |
| Diagnostics                                 |   ✅   | Download diagnostics from the integration page                     |
| Cover position feedback (open/closed state) |   ❌   | Not tracked — the daily schedule sends its commands without reading the covers' position; only heat protection skips covers that already read `closed` |

---

## 📄 License

This project is licensed under the MIT License.


