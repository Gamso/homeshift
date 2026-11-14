# Changelog

## Unreleased

### ⚠️ Upgrade notes

- **Requires Home Assistant 2026.11.0** or later (it was 2026.9.0).

### 🔧 Development

- Tests run on `pytest-homeassistant` (Home Assistant's own test package, 2026.11.1) instead of the deprecated `pytest-homeassistant-custom-component`, on Python 3.14.

## 2.1.0

Changes since **2.0.0**. This release replaces the 2.1.0 betas (`2.1.0_b2`, `2.1.0_b3`).

Requires Home Assistant **2026.9.0** or later.

### ⚠️ Upgrade notes

- **The card ships with the integration.** HomeShift serves it and loads it on every dashboard, with no dashboard resource to add. If you installed the separate HomeShift card (HACS and its resource), remove it: two cards with the same name conflict.

### ✨ New features

- **A restyled card.** A dark glass look that takes the colour of the thermostat mode (border, header icon, glow and particles: embers when heating, snowflakes when cooling, air streaks in ventilation, a slow breathing glow when off). The animations stop when the system asks for reduced motion. Based on [climate-card-holm](https://github.com/kaaribou/climate-card-holm) by kaaribou.
  - Each thermostat mode has its icon and button; the day mode is a dropdown next to the next mode and its start time.
  - The opening and closing times show roller shutter icons; a tap opens or closes the covers now.
  - Schedules panel: segmented tabs per day mode, hatched timelines for disabled schedules, ticked or crossed switches.
  - No setup: the card finds the HomeShift entities by itself, even renamed ones. The entity pickers are folded in an "Entities (advanced)" section of the editor.
- **Climate auto start/stop** for Versatile Thermostat switches. Each climate gets one setpoint threshold per thermostat mode (heating, cooling, fan), the same whatever the day mode. In heating the climate runs while its setpoint is at or above the threshold; in cooling and fan, while it is at or below. HomeShift reacts as soon as the setpoint changes. A thermostat mode left empty is not driven.
  - The card shows the setpoint against the threshold of each climate (for example "Setpoint 20° · runs from 19°"), in a foldable section where a tap flips a climate by hand.
- **Guided first setup.** Adding HomeShift asks for the calendars, then which mode each kind of day gets. Everything else is set afterwards from Configure.
- **Clearer options dialog.**
  - *Day mode* sets the calendar keywords per mode, one field each, instead of the `Keyword:key` syntax.
  - *Display names* has its own page for the names of the day modes and of the thermostat modes.
  - *Schedules* warns about the scheduler switches that have no thermostat tag.
  - *Covers → Cover list* is a single list: each cover is opened and closed every day 🕒 and/or protected from heat 🌡️.
  - *Opening and closing times* previews tonight's closing and tomorrow's sunrise opening.
  - *Climate auto start/stop* labels each threshold with its thermostat mode and shows the climate's current setpoint.
  - *Save configuration* moves to the top of the menu, with the number of sections changed; ✎ marks the sections changed and not saved yet.

### 🛠️ Improvements

- The card's URL carries a digest of its content, so a CDN or proxy such as Cloudflare no longer serves an outdated bundle.

### 📝 Documentation

- One page per feature, with screenshots, in English and French.
- Version, Home Assistant and licence badges on the home page.

## 2.0.0

Changes since **1.9.0**. This release replaces the 1.10.0 betas (`1.10.0_b`, `1.10.0_b2`, `1.10.0_b3`, `1.10.0_b4`).

Pairs with **HomeShift Card 2.0.0**.

Requires Home Assistant **2026.9.0** or later.

### ⚠️ Upgrade notes

- **The config entry migrates to version 5 automatically.** Schedulers are now stored by mode key (`home`, `work`, ...) instead of display name. This also fixes French instances that never opened *Mode Mapping*: their schedulers were stored under the English names, so none was ever turned on. A stored name that matches no mode is kept and logged.
- **Entity names are translated** and follow the instance language. Entity ids do not change: existing ids are kept, and new installs get the English ids (`select.homeshift_day_mode`, ...) whatever the language.
- **A thermostat mode change now drives climates**, not just scheduler switches (see below). The climates targeted by thermostat-tagged schedulers are switched or turned off when the thermostat mode changes.
- The integration is declared as a `service` (it was `hub`). The documentation link now points to `Gamso/homeshift`.

### ✨ New features

- **The thermostat mode drives the climates.**
  - **Off** turns off every climate a thermostat-tagged scheduler acts on.
  - **Heating / Cooling / Ventilation** switches the climates of that mode's schedulers to `heat` / `cool` / `fan_only` and runs the current slot of the enabled schedulers, so the setpoint applies right away.
  - Climates only driven by another mode's schedulers are turned off.
  - Climates that are already in the right mode, unavailable, or lacking the HVAC mode are left alone.
- **Open / close the covers on demand.**
  - New buttons `button.homeshift_open_covers` and `button.homeshift_close_covers`, and services `homeshift.open_covers` and `homeshift.close_covers`.
  - The close follows the evening close rules: it skips a cover behind an open window and uses the My position button.
  - These manual actions do not cancel the day's scheduled open or close.
- **Temporarily inhibit covers.**
  - `homeshift.inhibit_covers` takes covers out of the automation for a duration, until a date, or until resumed. `homeshift.resume_covers` hands them back.
  - An inhibited cover gets no open, close, window check or heat protection. Inhibiting or resuming never moves it.
  - New `sensor.homeshift_covers_inhibited` lists the inhibited covers and their end.
- **Close a cover once its window is shut.** A new option, *Close as soon as the window is shut* (off by default), lets a cover left up by an open window close when that window shuts during the night.
  - The wait lasts until the next morning open, survives restarts, and catches up on a window shut while Home Assistant was down.
  - A window shut in the daytime never lowers a cover.
- **Reorganized options dialog.**
  - The main menu lists Calendars, Day modes, Schedulers and Covers, each with a summary of its settings.
  - Covers is a sub-menu: Managed covers, Opening and closing times, Heat protection.
  - Unsaved sections are listed, and each form says where *Save* returns.
  - The forms use folded sections and show display names instead of raw keys.
  - Managed covers gain an *Edit a cover* entry.
- **Calendar outage on the card.** An amber banner says since when a calendar cannot be read and which day mode is kept; the day mode select exposes it as `calendar_error`.
- **Diagnostics.** Download them from the integration page for bug reports. They include the configuration, the coordinator data, today's cover schedule, the inhibitions and the covers waiting for their window.

### 🐛 Fixes

**Calendars and day mode**
- When a work or holiday calendar is unavailable or unknown, HomeShift keeps the current mode instead of reading it as "no event". A CalDAV or Google outage no longer switches the day to Work or cancels an absence. The outage is logged once, and so is its end.
- The cover schedule keeps running when a calendar cannot be read.
- A day-mode change that lands before the morning open recomputes today's opening time. Example: a calendar still showing Friday's remote-work event at midnight no longer opens the covers on Saturday at the weekday time.
- A calendar event whose end is already past is ignored, so the midnight switch happens on time.
- The manual override survives a Home Assistant restart.

**Covers**
- Heat protection stays active on *skip* days. It starts at the sunrise-based time when there is no opening time.
- Heat protection sends nothing when every protected cover is already closed, so a My press can no longer raise them.
- The evening close skips covers already lowered by hand and sends one command per cover. A cover that rejects the command no longer blocks the others, and a My button no longer raises a closed cover.
- A failed cover, button or scheduler command is logged and retried at the next poll. Before, the failure made every HomeShift entity unavailable, and a failed proactive close was never retried that day.

**Setup and entities**
- Timers are cancelled when the first setup fails. Before, a failed first setup could leave timers running on an orphaned coordinator.
- Conditional entities (cover time sensors, covers-left-open, heat protection, cover buttons) are removed from the registry once their feature is unconfigured. Before, they stayed behind as unavailable entities.
- The integration's storage files are deleted when the integration is removed.
- Translations: Away display field and selector options (cover action, per-mode opening time) are now translated in English and French.
- The calendar integration is loaded before HomeShift at startup.

### 📝 Documentation

- The README uses the real entity ids (`select.homeshift_day_mode`, ...). This fixes the notification automation example, which never triggered.
- The README documents the behaviors above and the thermostat-to-climate mapping.
- Corrected statements: the scan interval is a fixed 5 minutes, the holiday calendar is required, and the next-mode prediction looks 7 days ahead.

### 🔧 Development

- CI runs hassfest, the HACS action and ruff. Test dependencies are pinned to Home Assistant 2026.9.0.
- New tests run on a real Home Assistant instance: setup, unload, reload, outages, the French flow and entity ids. The test suite now uses native async tests.
- `scripts/init_calendars.py` reads the token from `HA_TOKEN` or a prompt instead of the command line. `starts_ha.sh` checks the SHA-256 of what it downloads.
- Cleanup: the config and options flows share one implementation, and stray files and the unknown `domain` key in `hacs.json` are gone.
