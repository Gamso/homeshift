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
  - [🛠️ Services](#️-services)
    - [`homeshift.refresh_schedulers`](#homeshiftrefresh_schedulers)
    - [`homeshift.check_next_day`](#homeshiftcheck_next_day)
  - [⚙️ Configuration Parameters](#️-configuration-parameters)
  - [🧠 Detection Logic](#-detection-logic)
    - [Half-Day Events](#half-day-events)
  - [🗓️ Scheduler Integration](#️-scheduler-integration)
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

HomeShift is a custom Home Assistant integration that automatically manages **day modes** (Home, Work, Telework, Absence…) and **thermostat modes** (Heating, Cooling, Off…) based on your calendar events, weekends, and public holidays.

Periodically (every 60 minutes by default), it reads today's and tomorrow's calendar, determines the appropriate day mode, and activates the matching scheduler switches — so your home is always in the right mode at the right time.

### How It Works

1. Reads events from a work/schedule calendar for the next day
2. Checks for public holidays via an optional holiday calendar
3. Determines the day mode (configurable mapping: event → mode)
4. Activates / deactivates scheduler switches tagged with the current day mode and thermostat mode

---

## ✅ Requirements

- Home Assistant 2023.1 or later
- A **calendar** entity for work/schedule events
- A **calendar** entity for public holidays
- [Scheduler integration](https://github.com/nielsfaber/scheduler-component) for scheduler management

---

## ⚙️ Quick Setup

1. Add the integration: **Settings → Devices & Services → Add Integration → HomeShift**
2. Select your work calendar entity
3. Optionally select a holiday calendar
4. Configure day modes and thermostat modes (or keep defaults)
5. Save — it starts working immediately

The integration will:
- Check the calendar periodically (every 60 minutes by default, configurable)
- Update `select.day_mode` automatically
- Activate / deactivate the matching scheduler switches

---

## 📊 Entities

### `select.day_mode`
Current day mode selector.

- **Type:** Select
- **Default options:** `Home`, `Work`, `Telework`, `Absence`
- **Writable:** Yes (manual override supported)

### `select.thermostat_mode`
Current thermostat mode selector.

- **Type:** Select
- **Default options:** `Off`, `Heating`, `Cooling`, `Ventilation`
- **Writable:** Yes

### `number.override_duration`
Duration (in minutes) during which automatic updates are blocked after a manual mode change.

- **Type:** Number
- **Default:** `0` (disabled)

---

## 🛠️ Services

### `homeshift.refresh_schedulers`
Manually trigger a refresh of scheduler switches based on the current day mode and thermostat mode.

### `homeshift.check_next_day`
Manually trigger the next-day detection and update `select.day_mode` accordingly.

---

## ⚙️ Configuration Parameters

All parameters are configurable via the Home Assistant UI (Integration Options).

| Parameter               | Default                            | Description                                       |
| ----------------------- | ---------------------------------- | ------------------------------------------------- |
| **Work Calendar**       | —                                  | Calendar entity with work/schedule events         |
| **Holiday Calendar**    | —                                  | Calendar entity for public holidays               |
| **Day Modes**           | `Home, Work, Telework, Absence`    | Comma-separated list of available day modes       |
| **Thermostat Mode Map** | `Off:Off, Heating:Heating, ...`    | Internal key → display label mapping              |
| **Scan Interval**       | `60 min`                           | How often the coordinator refreshes               |
| **Override Duration**   | `0` (disabled)                     | Minutes to block auto-updates after manual change |
| **Default Mode**        | `Work` / `Work`                    | Mode for regular work days                        |
| **Weekend Mode**        | `Home` / `Home`                    | Mode for Saturdays and Sundays                    |
| **Holiday Mode**        | `Home` / `Home`                    | Mode for public holidays                          |
| **Event Mode Map**      | `Vacation:Home, Telework:Telework` | Calendar event → day mode mapping                 |
| **Absence Mode**        | `Absence`                          | Mode that blocks automatic updates                |

---

## 🧠 Detection Logic

On every refresh cycle, the integration evaluates tomorrow using this priority order:

| Priority | Condition                                                 | Resulting mode                |
| -------- | --------------------------------------------------------- | ----------------------------- |
| 1        | Calendar event matches `event_mode_map` (e.g. "Vacation") | Mapped mode (e.g. `Home`)     |
| 2        | Tomorrow is Saturday or Sunday                            | `mode_weekend`                |
| 3        | Calendar event matches `event_mode_map` (e.g. "Telework") | Mapped mode (e.g. `Telework`) |
| 4        | Tomorrow is a public holiday (holiday calendar)           | `mode_holiday`                |
| 5        | Default                                                   | `mode_default` (e.g. `Work`)  |

> **Note:** If the current day mode is set to the **Absence mode**, automatic updates are blocked.

### Half-Day Events

Events that cover only the morning or afternoon are detected and the mode is applied only to the relevant half of the day.

---

## 🗓️ Scheduler Integration

HomeShift activates and deactivates scheduler switches based on the combination of **day mode** and **thermostat mode**.

Organize your scheduler switches with tags or names following this convention:

```
switch.schedulers_<thermostat_mode>_<day_mode>
```

Examples:
- `switch.schedulers_heating_home`
- `switch.schedulers_heating_work`
- `switch.schedulers_heating_telework`
- `switch.schedulers_heating_absence`

When the thermostat mode is `Off` (the internal `THERMOSTAT_OFF_KEY`), any scheduler switch that carries a **thermostat-mode tag** (e.g. `Heating`, `Cooling`) is force-disabled. Schedulers without a thermostat tag are left untouched.

---

## 📄 License

This project is licensed under the MIT License.