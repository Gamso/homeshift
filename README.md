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
    - [`select.day_mode`](#selectday_mode)
    - [`select.thermostat_mode`](#selectthermostat_mode)
    - [`number.override_duration`](#numberoverride_duration)
    - [`number.early_switch`](#numberearly_switch)
    - [`sensor.next_mode`](#sensornext_mode)
    - [`sensor.next_mode_at`](#sensornext_mode_at)
    - [`sensor.cover_open_time`](#sensorcover_open_time)
    - [`sensor.cover_close_time`](#sensorcover_close_time)
  - [🛠️ Services](#️-services)
    - [`homeshift.refresh_schedulers`](#homeshiftrefresh_schedulers)
    - [`homeshift.sync_calendar`](#homeshiftsync_calendar)
  - [⚙️ Configuration Parameters](#️-configuration-parameters)
  - [🧠 Detection Logic](#-detection-logic)
    - [Half-Day Events](#half-day-events)
    - [Early Switch](#early-switch)
  - [🗓️ Scheduler Integration](#️-scheduler-integration)
    - [Thermostat Tags](#thermostat-tags)
  - [🗓️ Daily Cover Schedule](#️-daily-cover-schedule)
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

At regular intervals (every 5 minutes by default), it reads your calendar, picks the right day mode, and turns the matching scheduler switches on or off — so your home adapts automatically without any manual intervention.

### How It Works

1. Reads the active event from your work/schedule calendar
2. Optionally checks a public holiday calendar
3. Determines the day mode based on a configurable event → mode mapping
4. Turns on the scheduler switches for the active mode, and turns off all others

---

## ✅ Requirements

- A **calendar** entity containing your work or schedule events
- A **calendar** entity for public holidays
- The [Scheduler integration](https://github.com/nielsfaber/scheduler-component) to automate scheduler switches

> **Scheduler tags (required for thermostat integration):** When using the Scheduler integration alongside `thermostat_mode`, each scheduler switch that controls heating or cooling **must have the matching thermostat tag** (e.g. `Heating`, `Cooling`). Schedulers without any thermostat tag are treated as day-mode-only and are never force-disabled by the thermostat logic. See the [Thermostat Tags](#thermostat-tags) section for details.

---

## ⚙️ Quick Setup

1. Go to **Settings → Devices & Services → Add Integration → HomeShift**
2. Select your work calendar entity
3. Optionally select a holiday calendar
4. Configure your day modes and thermostat modes, or keep the defaults
5. Save — HomeShift starts working immediately

Once set up, HomeShift will:
- Periodically read your calendar (every 5 minutes by default)
- Automatically update `select.day_mode`
- Turn the right scheduler switches on and off

---

## 📊 Entities

### `select.day_mode`
Shows and controls the current day mode. HomeShift updates it automatically based on your calendar, but you can also change it manually at any time.

- **Type:** Select
- **Default options:** `Home`, `Work`, `Remote`, `Away`
- **Writable:** Yes — a manual change can be protected from auto-updates using the override duration

### `select.thermostat_mode`
Shows and controls the current thermostat mode.

- **Type:** Select
- **Default options:** `Off`, `Heating`, `Cooling`, `Ventilation`
- **Writable:** Yes

### `number.override_duration`
When you manually change the day mode, this setting defines how long (in minutes) HomeShift waits before resuming automatic updates. Set to `0` to always allow automatic updates.

- **Type:** Number
- **Default:** `0` (disabled)

---

### `number.early_switch`
Pre-activates an upcoming timed calendar event before it officially starts. When set, HomeShift switches to the correct day mode up to X minutes before the event start.

- **Type:** Number (minutes, 0–480, step 5)
- **Default:** `0` (disabled)
- **Only applies to timed events** — all-day events are always ignored.

**Example:** You have a *Remote work* event from 14:00 to 18:00 and `early_switch = 120`. HomeShift will switch to `Remote working` mode at **12:00**, giving your heating schedule 2 hours to warm the house before you start working.

The `sensor.next_mode_at` and `sensor.next_mode` sensors reflect this anticipated switch time, so you can display it on a dashboard.

---

### `sensor.next_mode`
Shows the predicted next day mode that HomeShift will switch to.

- **Type:** Sensor (text)
- **Value:** Display name of the predicted next mode (e.g. `Remote working`). When no change is expected in the next 2 days, shows the current day mode.

### `sensor.next_mode_at`
Shows when the next automatic mode change is expected to occur (taking early_switch into account for timed events).

- **Type:** Sensor (timestamp)
- **Unit:** ISO 8601 datetime

### `sensor.cover_open_time`
Shows the cover opening time computed for today by the Daily Cover Schedule feature.

- **Type:** Sensor (text)
- **Value:** `HH:MM` string (e.g. `07:45`), or `unknown` if not configured or has not run yet.
- **Only registered** when **Daily Cover Entities** is configured.

### `sensor.cover_close_time`
Shows the daily cover closing time computed for today (today's sunset + offset) by the Daily Cover Schedule feature.

- **Type:** Sensor (text)
- **Value:** `HH:MM` string (e.g. `21:40`), or `unknown` if not configured or not yet computed.
- **Only registered** when **Daily Cover Entities** is configured.

---

## 🛠️ Services

### `homeshift.refresh_schedulers`
Immediately refreshes the scheduler switches based on the current day mode and thermostat mode. Useful after manually changing a mode.

### `homeshift.sync_calendar`
Manually triggers a calendar check and updates `select.day_mode` if needed. This is also called automatically at regular intervals.

---

## ⚙️ Configuration Parameters

All parameters can be changed at any time via **Settings → Devices & Services → HomeShift → Configure**.

| Parameter                 | Default                         | Description                                                   |
| ------------------------- | ------------------------------- | ------------------------------------------------------------- |
| **Work Calendar**         | —                               | Calendar entity containing your work/schedule events          |
| **Holiday Calendar**      | —                               | Calendar entity for public holidays (optional)                |
| **Day Modes**             | `Home, Work, Remote, Away`      | Comma-separated list of available day modes                   |
| **Thermostat Mode Map**   | `off:Off, heating:Heating, ...` | Maps internal thermostat keys to the display names you prefer |
| **Scan Interval**         | `5 min`                         | How often HomeShift checks the calendar (in minutes)          |
| **Override Duration**     | `0` (disabled)                  | Minutes to block automatic updates after a manual mode change |
| **Early Switch**          | `0` (disabled)                  | Minutes to pre-activate a timed event before its start        |
| **Default Mode**          | `Work`                          | Mode used on regular weekdays with no calendar event          |
| **Weekend Mode**          | `Home`                          | Mode used on Saturdays and Sundays                            |
| **Holiday Mode**          | `Home`                          | Mode used on public holidays                                  |
| **Event Mode Map**        | `Vacation:home, Remote:remote`  | Maps calendar event names to day modes                        |
| **Away Mode**             | `Away`                          | When this mode is active, automatic updates are paused        |
| **Cover Entities**        | —                               | Cover entities to close when it is too hot (optional; requires Daily Cover Entities below to be configured too) |
| **Temperature Sensor**    | —                               | Sensor providing the outdoor temperature                      |
| **Temperature Threshold** | `30 °C`                         | Temperature above which covers close reactively (fallback for days the forecast misses) |
| **Cover Action**          | `close_cover`                   | Service called when heat protection triggers: `close_cover` or `stop_cover` |
| **My Position Button**    | —                               | Button entity to press instead of a cover service (e.g. Somfy RTS "My" position) |
| **Weather Entity**        | —                               | Weather entity with daily forecasts, used for the proactive close (optional) |
| **Forecast Threshold**    | `28 °C`                         | Forecast daily high above which covers close proactively      |
| **Daily Cover Entities**  | —                               | Cover entity/group opened and closed daily (optional, separate from Cover Entities above); Cover Heat Protection's active window is derived from this |
| **Open Time — *(per day mode)*** | `08:30`                  | One field per day mode: `sunrise`, `skip`, or a custom `HH:MM` value |
| **Earliest Open Time**    | `07:00`                         | Floor time used when a day mode's Open Time is `sunrise`      |
| **Close Offset After Sunset** | `10 min`                    | Covers close this many minutes after sunset, every day, for every mode |

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

> **Note:** If the day mode is currently set to the **Away mode**, all automatic updates are paused until you change it manually.

### Half-Day Events

If a calendar event covers only the morning or only the afternoon, HomeShift applies the corresponding mode only during that half of the day, then reverts to the default mode for the other half.

### Early Switch

The `number.early_switch` entity lets you anticipate timed calendar events. When the current time is within the early-switch window before a timed event, HomeShift pre-activates the corresponding mode.

```
Calendar event:  Remote working  14:00 ──────────── 18:00
early_switch = 120 min
                             ↑
                          12:00  ← HomeShift switches to Remote working here
```

**Key rules:**
- Only applies to **timed events** (events with a specific start/end time). All-day events (e.g. public holidays) are never pre-activated.
- The `sensor.next_mode` and `sensor.next_mode_at` sensors reflect the anticipated switch time, not the original event start.
- Setting `early_switch` to `0` disables the feature entirely.

---

## 🗓️ Scheduler Integration

HomeShift can automatically turn scheduler switches on and off based on the current day mode.

In the integration settings, you can assign one or more switch entities to each day mode. When the day mode changes:
- The switches for the **active mode** are turned **on**
- The switches for **all other modes** are turned **off**

This lets you, for example, run different heating schedules depending on whether you're working from home or at the office — without any automation to write.

### Thermostat Tags

When you also use `thermostat_mode`, HomeShift needs to know which scheduler switches control heating or cooling so it can disable them automatically when the thermostat is off.

To make this work, each scheduler switch that is linked to a specific thermostat mode **must have the corresponding thermostat mode name set as a tag** in the Scheduler card.

**Example:**

Suppose your thermostat modes are `Heating` and `Cooling`. You create the following schedulers:

| Scheduler switch                 | Tags       | Purpose                                   |
| -------------------------------- | ---------- | ----------------------------------------- |
| `switch.schedule_home_heating`   | `Heating`  | Heating schedule when you're at home      |
| `switch.schedule_work_heating`   | `Heating`  | Heating schedule when you're at work      |
| `switch.schedule_home_cooling`   | `Cooling`  | Cooling schedule when you're at home      |
| `switch.schedule_presence_light` | *(no tag)* | Lighting schedule, not thermostat-related |

When `thermostat_mode` is set to **Off**, HomeShift will force-disable all switches tagged with `Heating` or `Cooling`, regardless of the current day mode. Switches without any thermostat tag (like `switch.schedule_presence_light`) are left untouched.

> **How to add a tag in the Scheduler card:** Open the Scheduler card → edit a schedule → scroll to *Tags* → add the thermostat mode name exactly as defined in your thermostat mode map (e.g. `Heating`, `Cooling`).

---

## 🗓️ Daily Cover Schedule

HomeShift can natively open and close a cover (typically a cover group) every day, without depending on any Scheduler-integration entity. **Daily Cover Entities** is its own entity list, separate from Cover Heat Protection's **Cover Entities** — so a whole-house cover group can follow the daily open/close schedule below while a single south-facing cover stays under heat-protection's control. [Cover Heat Protection](#️-cover-heat-protection) derives its active window from the times computed here, so configure this feature first.

Once per day, shortly after midnight, HomeShift computes:
- **Open time** — resolved per day mode. Each configured day mode has its own **Open Time** field, set to one of:
  - `sunrise` — sunrise, floored at **Earliest Open Time** (e.g. never before `07:00`)
  - `skip` — no automatic opening for that mode (covers stay as they are)
  - a custom `HH:MM` value — a fixed clock time
  
  Day modes sharing the same value effectively form a batch (e.g. both `Work` and `Remote` set to `sunrise`). A day mode with no value configured falls back to `08:30`. There's no separate "skip modes" list — set a mode's Open Time to `skip` directly.
- **Close time** — today's sunset plus **Close Offset After Sunset**, always, for every day mode (closing is not mode-dependent)

Then, on every coordinator poll, it opens the covers once now reaches the open time, and closes them once now reaches the close time — each action firing at most once per calendar day. Timing resolution matches the poll interval (5 minutes by default), not the exact minute.

**`sensor.cover_open_time`** and **`sensor.cover_close_time`** reflect today's computed times, so you can display them on your dashboard.

> **Migrating from Scheduler-integration volet entities:** if you previously used two Scheduler entities (a fixed/sunrise-based "open" and a sunset-offset "close") purely to drive covers, you can disable/delete them once Daily Cover Schedule is configured with the same times — HomeShift no longer needs the Scheduler integration for covers at all.

---

## ☀️ Cover Heat Protection

HomeShift can automatically close a cover to prevent heat build-up — without requiring any separate automation, and without a separately configured time window. Once closed by this automation, the cover stays closed for the rest of the day; it never reopens itself. It's touched again either by the next day's normal open, or by Daily Cover Schedule's own unconditional evening close.

**Cover Heat Protection now requires [Daily Cover Schedule](#️-daily-cover-schedule) to be configured.** Its active window isn't set independently — it's exactly `[cover_open_time, daily_close_time]`, the same times Daily Cover Schedule already computes every day. This also means: if it's already hot right when the cover would normally open for the day, heat protection can apply the closed/protected position immediately instead of opening it and closing it again moments later.

### Reactive Close

Each time the coordinator runs **and** whenever the temperature sensor value changes, HomeShift checks: if the cover hasn't already been closed by this automation today, and the current time is within today's `[cover_open_time, daily_close_time]` window, and the outdoor temperature exceeds **Temperature Threshold**, it applies the configured **Cover Action**: `close_cover` (default), `stop_cover` (interrupts movement mid-travel — useful for Somfy RTS covers), or presses the **My Position Button** if one is configured (sends the cover to its pre-recorded favourite position).

This fires at most once per day — once closed, HomeShift leaves the cover alone regardless of what the temperature does afterward.

### Proactive Forecast-Based Close

If a **Weather Entity** (with daily forecasts) is configured, HomeShift also checks — once per day, at today's `cover_open_time` — whether today's forecast high exceeds **Forecast Threshold**. If it does, the cover closes immediately (or skips opening in the first place, if this runs before/at the same moment Daily Cover Schedule opens it), ahead of the outdoor sensor actually crossing the reactive threshold.

The reactive close above still runs during the rest of the window as a fallback, in case the forecast lookup fails or under-predicts the day.

Leave **Weather Entity** unset to disable the proactive close entirely; behavior then falls back to the reactive close only.

### State Persistence

Whether the cover has already been closed by this automation today, and when the forecast was last checked, are persisted to storage, so a Home Assistant restart mid-day doesn't lose track of the day's state. The same storage also tracks whether today's Daily Cover Schedule open/close actions have already run, for the same reason.

---

## 🧩 Feature Support

| Feature                                    | Status | Notes                                                              |
| ------------------------------------------- | :----: | -------------------------------------------------------------------|
| Calendar-driven day mode                    |   ✅   | See [Detection Logic](#-detection-logic)                           |
| Thermostat mode + scheduler tags            |   ✅   | See [Thermostat Tags](#thermostat-tags)                            |
| Half-day event support                      |   ✅   | See [Half-Day Events](#half-day-events)                            |
| Early switch (pre-activation)               |   ✅   | See [Early Switch](#early-switch)                                  |
| Manual override with timeout                |   ✅   | `number.override_duration`                                         |
| Native daily cover open/close (no Scheduler entity needed) | ✅ | See [Daily Cover Schedule](#️-daily-cover-schedule)                |
| Daily cover schedule state survives HA restart |  ✅  | Persisted alongside the heat-protection cover state                |
| Cover reactive heat close                   |   ✅   | See [Reactive Close](#reactive-close); active window derived from Daily Cover Schedule; never reopens itself |
| Cover proactive forecast-based close        |   ✅   | See [Proactive Forecast-Based Close](#proactive-forecast-based-close) |
| Cover automation state survives HA restart  |   ✅   | See [State Persistence](#state-persistence)                        |
| Day-mode/thermostat-mode state survives HA restart |  ✅  | Restored from storage at startup                             |
| Cover position feedback (open/closed state) |   ❌   | Not tracked — commands are sent blind; HomeShift only tracks whether *it* closed a cover today, not the cover's actual position |

---

## 📄 License

This project is licensed under the MIT License.


