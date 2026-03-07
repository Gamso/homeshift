# HomeShift — Copilot Instructions

## Project Overview
HomeShift is a Home Assistant custom integration (distributed via HACS) that automatically manages `select.day_mode` and `select.thermostat_mode` entities based on calendar events, weekends, and public holidays. It drives on/off state of optional [Scheduler](https://github.com/nielsfaber/scheduler-component) switches.

## Architecture

```
coordinator.py          ← All logic lives here (HomeShiftCoordinator extends DataUpdateCoordinator)
├── __init__.py         ← HA entry setup, service registration, lifecycle management
├── select.py           ← Thin CoordinatorEntity wrappers for day_mode and thermostat_mode
├── number.py           ← CoordinatorEntity wrapper for override_duration
├── config_flow.py      ← Multi-step UI: menu → calendars → mapping → schedulers → finalize
├── const.py            ← All constants, defaults, and LOCALIZED_DEFAULTS (en/fr)
└── services.yaml       ← homeshift.refresh_schedulers, homeshift.sync_calendar
```

**Data flow:** Periodic calendar poll (default 60 min) → `coordinator.async_update_data()` → sets `day_mode` → calls `async_refresh_schedulers()` to toggle scheduler switch entities.

## Critical Patterns

### Mode Map Format
All mode maps use `"key:DisplayName, key2:DisplayName2"` strings. **Keys are stable English identifiers; display names are locale-specific.** Never hardcode display names in logic — always work with keys internally.

```python
# In const.py
DEFAULT_DAY_MODE_MAP = "home:Home, work:Work, remote:Remote, away:Away"

# Parsed via coordinator
self._day_mode_map: dict[str, str]  # {"home": "Maison", "work": "Travail", ...} (FR locale)
```

### Config Merging
Options flow entries always override data entries. Access config consistently:
```python
_config = {**entry.data, **entry.options}  # options take precedence
```
`coordinator._config` property does this merge. Never read `entry.data` directly in the coordinator.

### Localization
`LOCALIZED_DEFAULTS` in `const.py` holds per-locale defaults (currently `en`, `fr`). `get_localized_defaults(hass)` resolves based on `hass.config.language`, falling back to `"en"`. The config flow and coordinator both use this for initial defaults.

### `today_type` Persistence
The coordinator persists `_today_type` (the matched event keyword, e.g. `"télétravail"`) across the entire day to avoid mode flickering between half-day events. It resets at midnight when `_today_date` changes.

### State Persistence Across Restarts
Day/thermostat mode keys are saved to HA storage (`Store`) and restored in `async_restore_state()` before the first coordinator refresh.

## Developer Workflows

| Task | Command |
|---|---|
| Start HA (port 8123) | `./container start` |
| Restart HA | `./container restart` |
| Run tests with coverage | `./container coverage` |
| Run tests directly | `pytest tests/` |
| Validate integration manifest | `./container hassfest` |
| Update translations | `./container translations` |

## Testing Conventions

- Tests use **French locale** as the default (`hass.config.language = "fr"`) — assert against French display names (`"Maison"`, `"Travail"`, not `"Home"`, `"Work"`).
- Shared fixtures are in `tests/conftest.py`: `make_mock_hass()`, `make_mock_entry()`, `make_calendar_state()`.
- Test files are split by concern: `test_coordinator.py` (utilities/scan interval), `test_coordinator_modes.py` (mode logic, half-day, absence), `test_coordinator_features.py` (features), `test_init.py`, `test_calendars.py`.
- Coordinator is tested directly (no HA test harness) by mocking `hass` and `ConfigEntry` via `MagicMock`.
- `asyncio_mode = auto` is set; no need for `@pytest.mark.asyncio`.

## Adding a New Mode or Config Option

1. Add the constant to `const.py` (`CONF_*`, `DEFAULT_*`).
2. Add it to `LOCALIZED_DEFAULTS["en"]` and `LOCALIZED_DEFAULTS["fr"]`.
3. Add a schema field in `config_flow.py` (options flow if runtime-adjustable).
4. Read it in `HomeShiftCoordinator.__init__` following the `_config.get(CONF_X, _loc.get(CONF_X, DEFAULT_X))` pattern.
5. Add translation strings to both `translations/en.json` and `translations/fr.json`.

## Key Files for Reference
- [custom_components/homeshift/coordinator.py](../custom_components/homeshift/coordinator.py) — core logic
- [custom_components/homeshift/const.py](../custom_components/homeshift/const.py) — all constants and localized defaults
- [custom_components/homeshift/config_flow.py](../custom_components/homeshift/config_flow.py) — UI configuration flow
- [tests/conftest.py](../tests/conftest.py) — shared test fixtures
