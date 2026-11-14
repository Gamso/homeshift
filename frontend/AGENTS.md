# Instructions for the HomeShift card

These rules guide AI agents working on the HomeShift card, bundled with the integration (sources in `frontend/`). Focus on the current patterns and workflows used here.

## Architecture Overview

- **Entry point:** [src/index.ts](src/index.ts) registers the card in `window.customCards` and imports the implementation module.
- **Config:** [src/types.ts](src/types.ts) exports `HomeShiftCardConfig` and `ENTITY_FIELDS`, the single table of entity options (key, picker domains, default entity). The card's defaults, its watched entities and the editor's pickers are all derived from it.
- **Main card:** [src/components/homeshift-card.ts](src/components/homeshift-card.ts) defines `HomeShiftCard` (Lit 3), registered as `homeshift-card`: a dark glass card coloured by the thermostat mode (`--m`): header, thermostat mode as segmented `<button>`s, day mode combobox and next mode tiles, the two collapsible minutes settings (stepper), cover times / "open-close now" buttons, then the alert chips.
- **Editor:** [src/components/homeshift-card-editor.ts](src/components/homeshift-card-editor.ts) defines `homeshift-card-editor`, one `ha-entity-picker` per `ENTITY_FIELDS` entry.
- **State helpers:** [src/state.ts](src/state.ts) (`isUsable`, `numericState`, `formatMinutes`) and [src/time.ts](src/time.ts) (time formatting from `hass.locale`).
- **Localization:** [src/localize/localize.ts](src/localize/localize.ts) provides `localize(hass, key, params?, fallback?)` using [src/localize/en.json](src/localize/en.json) and [src/localize/fr.json](src/localize/fr.json). Lookup: user language, English, `fallback`, then the key.
- **Build artifacts:** Rollup outputs a minified ES module to `custom_components/homeshift/www/homeshift-card.js` (not committed, no sourcemap; the Release workflow builds it into `homeshift.zip`); the integration serves it as `/homeshift/homeshift-card.js` and loads it in every dashboard.

## Build & Dev Workflows

- **Install & build:** `npm ci` then `npm run build` (Rollup; see [rollup.config.js](rollup.config.js)). Never commit the bundle (it is git-ignored): commit the sources only.
- **Checks:** `npm run typecheck`, `npm run lint`, `npm test` (Vitest + happy-dom, tests in `test/`).
- **Watch mode:** `npm run watch` for incremental builds.
- **In Home Assistant:** the integration's DevContainer runs HomeShift, which loads the bundle; rebuild, then reload the browser page.

## Card Patterns

- **Registration:** keep the `customElements.get(...)` guards before `customElements.define("homeshift-card", ...)`, and the `window.customCards.push({...})` in [src/index.ts](src/index.ts).
- **Config handling:** add an entity option to `HomeShiftCardConfig` and `ENTITY_FIELDS` (plus an `editor.<key>` label in both JSON files); `setConfig` applies the defaults. Keys: `name` (accepted, not displayed), `day_mode_entity`, `thermostat_mode_entity`, `override_duration_entity`, `early_switch_entity`, `next_mode_entity`, `next_mode_at_entity`, `heat_protection_entity`, `cover_open_time_entity`, `cover_close_time_entity`, `open_covers_entity`, `close_covers_entity`, `cover_entity` (legacy, overrides the buttons), `covers_left_open_entity`.
- **State access:** read entities with `getEntityState()`; filter `unknown` / `unavailable` with `isUsable()` before displaying a state.
- **Missing entities:** stub data is only used when HA sets `preview`; otherwise show `card.entity_not_found`.
- **Service calls:** `select.select_option` (day / thermostat mode), `number.set_value` (steppers), `button.press` on the integration buttons (or `cover.open_cover` / `close_cover` for a legacy `cover_entity`). Report failures with a `hass-notification` event, never leave a promise unhandled.
- **Accessibility:** interactive elements are `<button>`s (the day mode is a `role="combobox"` button with a listbox) with a localized `aria-label`; no hover-only information.
- **Styling:** add styles under `static styles = css\`...\``; the card is always dark: use its own variables (`--m`, `--hs-text`, `--hs-text-2`, `--hs-surface`, `--hs-ring`), and honour `prefers-reduced-motion`.

## Localization Conventions

- **Keys:** dot paths like `card.entity_not_found`, `editor.day_mode_entity`, `thermostat.heating`.
- **Params:** `localize(this.hass, "card.entity_not_found", { entity: id })`.
- **Both languages:** add every key to `en.json` and `fr.json`; tests enforce identical key sets and fail on a key no source file uses.

## Safe Changes for Agents

- **Minimal diffs:** change only what's needed; preserve the public API (`HomeShiftCard`, tag names, config keys).
- **Tests:** add a Vitest test in `test/` for every bug fix or new option.
- **Build output:** do not rename `homeshift-card.js`: `custom_components/homeshift/frontend.py` serves it under that name.
