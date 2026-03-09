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
  - [🛠️ Services](#️-services)
    - [`homeshift.refresh_schedulers`](#homeshiftrefresh_schedulers)
    - [`homeshift.sync_calendar`](#homeshiftsync_calendar)
  - [⚙️ Configuration Parameters](#️-configuration-parameters)
  - [🧠 Detection Logic](#-detection-logic)
    - [Half-Day Events](#half-day-events)
    - [Early Switch](#early-switch)
  - [🗓️ Scheduler Integration](#️-scheduler-integration)
    - [Thermostat Tags](#thermostat-tags)
  - [🌅 Sunrise Scheduler Adjustment](#-sunrise-scheduler-adjustment)
  - [☀️ Cover Heat Protection](#️-cover-heat-protection)
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
- **Value:** Display name of the predicted mode (e.g. `Remote working`), or `unknown` if no change is expected in the next 2 days.

### `sensor.next_mode_at`
Shows when the next automatic mode change is expected to occur (taking early_switch into account for timed events).

- **Type:** Sensor (timestamp)
- **Unit:** ISO 8601 datetime

### `sensor.cover_open_time`
Shows the cover opening time computed for today by the Sunrise Scheduler Adjustment feature.

- **Type:** Sensor (text)
- **Value:** `HH:MM` string (e.g. `07:45`), or `unknown` if the feature is not configured or has not run yet.
- **Only registered** when at least one scheduler entity is listed in **Sunrise Schedulers**.

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
| **Cover Entities**        | —                               | Cover entities to close when it is too hot (optional)         |
| **Temperature Sensor**    | —                               | Sensor providing the outdoor temperature                      |
| **Temperature Threshold** | `30 °C`                         | Temperature above which covers are closed                     |
| **Heat Window Start**     | `08:00`                         | Earliest time of day the heat protection is active            |
| **Heat Window End**       | `20:00`                         | Latest time of day the heat protection is active              |
| **Sunrise Schedulers**    | —                               | Scheduler switch entities whose opening time tracks sunrise   |
| **Earliest Open Time**    | `07:10`                         | Minimum opening time even when sunrise is earlier             |

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

## 🌅 Sunrise Scheduler Adjustment

HomeShift can adjust the opening time of scheduler switches every morning based on today's actual sunrise time.

Each day shortly after midnight, HomeShift computes:
```
target_time = max(sunrise_local, earliest_open_time)
```
and calls `scheduler.edit` on each configured scheduler entity to update its first timeslot start time.

**Configuration:**
- **Sunrise Schedulers** — list of `switch.schedule_*` entities to update
- **Earliest Open Time** — floor time so covers never open before a fixed hour (e.g. `07:10`)

**`sensor.cover_open_time`** reflects the time that was applied this morning, so you can display it on your dashboard.

---

## ☀️ Cover Heat Protection

HomeShift can automatically close covers when the outdoor temperature exceeds a threshold during a configurable time window. This prevents heat build-up without requiring any automation.

Each time the coordinator runs **and** whenever the temperature sensor value changes, HomeShift checks:
- Is the current time within the configured active window?
- Is the temperature above the configured threshold?

If both conditions are met, `cover.stop_cover` is called on all configured cover entities. For Somfy covers this closes the cover to their pre-recorded favourite position.

**Configuration:**
- **Cover Entities** — covers to control
- **Temperature Sensor** — sensor providing the current outdoor temperature
- **Temperature Threshold** — temperature above which covers are closed (default: `30 °C`)
- **Heat Window Start / End** — time range during which the feature is active (default: `08:00–20:00`)

---

## 📄 License

This project is licensed under the MIT License.


