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
    - [`homeshift.sync_calendar`](#homeshiftsync_calendar)
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

HomeShift is a custom Home Assistant integration that automatically manages **day modes** (e.g. Home, Work, Remote, Absence) and **thermostat modes** (e.g. Heating, Cooling, Off) based on your calendar events, weekends, and public holidays.

At regular intervals (every 60 minutes by default), it reads your calendar, picks the right day mode, and turns the matching scheduler switches on or off — so your home adapts automatically without any manual intervention.

### How It Works

1. Reads the active event from your work/schedule calendar
2. Optionally checks a public holiday calendar
3. Determines the day mode based on a configurable event → mode mapping
4. Turns on the scheduler switches for the active mode, and turns off all others

---

## ✅ Requirements

- Home Assistant 2023.1 or later
- A **calendar** entity containing your work or schedule events
- Optionally, a **calendar** entity for public holidays
- Optionally, the [Scheduler integration](https://github.com/nielsfaber/scheduler-component) if you want to automate scheduler switches

---

## ⚙️ Quick Setup

1. Go to **Settings → Devices & Services → Add Integration → HomeShift**
2. Select your work calendar entity
3. Optionally select a holiday calendar
4. Configure your day modes and thermostat modes, or keep the defaults
5. Save — HomeShift starts working immediately

Once set up, HomeShift will:
- Periodically read your calendar (every 60 minutes by default)
- Automatically update `select.day_mode`
- Turn the right scheduler switches on and off

---

## 📊 Entities

### `select.day_mode`
Shows and controls the current day mode. HomeShift updates it automatically based on your calendar, but you can also change it manually at any time.

- **Type:** Select
- **Default options:** `Home`, `Work`, `Remote`, `Absence`
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

## 🛠️ Services

### `homeshift.refresh_schedulers`
Immediately refreshes the scheduler switches based on the current day mode and thermostat mode. Useful after manually changing a mode.

### `homeshift.sync_calendar`
Manually triggers a calendar check and updates `select.day_mode` if needed. This is also called automatically at regular intervals.

---

## ⚙️ Configuration Parameters

All parameters can be changed at any time via **Settings → Devices & Services → HomeShift → Configure**.

| Parameter               | Default                            | Description                                                   |
| ----------------------- | ---------------------------------- | ------------------------------------------------------------- |
| **Work Calendar**       | —                                  | Calendar entity containing your work/schedule events          |
| **Holiday Calendar**    | —                                  | Calendar entity for public holidays (optional)                |
| **Day Modes**           | `Home, Work, Remote, Absence`    | Comma-separated list of available day modes                   |
| **Thermostat Mode Map** | `Off:Off, Heating:Heating, ...`    | Maps internal thermostat keys to the display names you prefer |
| **Scan Interval**       | `60 min`                           | How often HomeShift checks the calendar (in minutes)          |
| **Override Duration**   | `0` (disabled)                     | Minutes to block automatic updates after a manual mode change |
| **Default Mode**        | `Work`                             | Mode used on regular weekdays with no calendar event          |
| **Weekend Mode**        | `Home`                             | Mode used on Saturdays and Sundays                            |
| **Holiday Mode**        | `Home`                             | Mode used on public holidays                                  |
| **Event Mode Map**      | `Vacation:Home, Remote:Remote` | Maps calendar event names to day modes                        |
| **Absence Mode**        | `Absence`                          | When this mode is active, automatic updates are paused        |

---

## 🧠 Detection Logic

Each time HomeShift refreshes, it looks at today's active calendar event and determines the day mode using this priority order:

| Priority | Condition                                        | Resulting mode                 |
| -------- | ------------------------------------------------ | ------------------------------ |
| 1        | Active calendar event matches the event mode map | Mapped mode (e.g. `Remote`)  |
| 2        | Today is Saturday or Sunday                      | **Weekend mode**               |
| 3        | Today is a public holiday                        | **Holiday mode**               |
| 4        | No special condition                             | **Default mode** (e.g. `Work`) |

> **Note:** If the day mode is currently set to the **Absence mode**, all automatic updates are paused until you change it manually.

### Half-Day Events

If a calendar event covers only the morning or only the afternoon, HomeShift applies the corresponding mode only during that half of the day, then reverts to the default mode for the other half.

---

## 🗓️ Scheduler Integration

HomeShift can automatically turn scheduler switches on and off based on the current day mode.

In the integration settings, you can assign one or more switch entities to each day mode. When the day mode changes:
- The switches for the **active mode** are turned **on**
- The switches for **all other modes** are turned **off**

This lets you, for example, run different heating schedules depending on whether you're working from home or at the office — without any automation to write.

---

## 📄 License

This project is licensed under the MIT License.


