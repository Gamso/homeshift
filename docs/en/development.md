# Development

[← Documentation](../../README.md#documentation) · [Français](../fr/development.md)

## Repository layout

```
custom_components/homeshift/   The integration
  www/homeshift-card.js        The card's bundle, built from frontend/ (not committed)
frontend/                      The card's sources (TypeScript, Lit), see frontend/README.md
tests/                         Integration tests (pytest)
docs/                          This documentation (en/, fr/, images/)
.devcontainer/, container,     A Home Assistant to try it in, with simulated entities
scripts/
```

## Integration

Python 3.14.2 or newer, Home Assistant 2026.11 or newer.

```bash
pip install -r requirements_test.txt
pytest
ruff check custom_components tests scripts
```

Tests run against a real Home Assistant (`pytest-homeassistant`) for the setup, entities and options flow, and against mocks for the coordinator's logic.

## Card

The card's sources live in `frontend/`; run the commands from there (Node 24):

```bash
npm ci
npm run build      # writes ../custom_components/homeshift/www/homeshift-card.js
npm run typecheck
npm run lint
npm test
```

The bundle is not committed: commit the sources only. The integration serves that file under `/homeshift/homeshift-card.js` and loads it in every dashboard (`custom_components/homeshift/frontend.py`); after a build, reload the browser page. Without a build, HomeShift runs without its card and logs a warning.

The card is documented for users in [The card](card.md).

## Devcontainer

**Dev Containers: Reopen in Container** in VS Code builds the card, then starts a Home Assistant on http://localhost:8123 with HomeShift, the Scheduler integration and its card, sample schedules, simulated covers, an outdoor temperature and two simulated auto start/stop switches. `./container card` rebuilds the card and `./container restart` restarts Home Assistant.

## Continuous integration

- **Tests**: pytest
- **Validate**: hassfest, HACS, ruff, pyright, the card (typecheck, lint, tests, build)
- **Release**: when a GitHub release is published, builds the card and attaches `homeshift.zip` (the contents of `custom_components/homeshift/`, card included) to it. HACS installs that archive (`zip_release` in `hacs.json`). It can be run by hand on an existing tag (*Run workflow*).

## Releasing

Set the version in `manifest.json`, merge, then publish a GitHub release whose tag is that version: the **Release** workflow attaches `homeshift.zip`. A release without that archive cannot be installed by HACS.

## Documentation

The documentation exists in English (`docs/en/`) and French (`docs/fr/`), with the same pages; change both. The card screenshots (`docs/images/card/en/` and `fr/`) are the card rendered with simulated data, in each language. The screenshots of the options dialog (`docs/images/options/en/` and `fr/`) are taken in the devcontainer, once with the test user's profile language in English and once in French; the day mode names stay in French there because the test instance was set up in French.
