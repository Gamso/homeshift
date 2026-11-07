# Development

[← Documentation](../../README.md#documentation) · [Français](../fr/development.md)

## Repository layout

```
custom_components/homeshift/   The integration
  www/homeshift-card.js        The card's bundle, built from frontend/ (committed)
frontend/                      The card's sources (TypeScript, Lit), see frontend/README.md
tests/                         Integration tests (pytest)
docs/                          This documentation (en/, fr/, images/)
.devcontainer/, container,     A Home Assistant to try it in, with simulated entities
scripts/
```

## Integration

Python 3.14, Home Assistant 2026.9 or newer.

```bash
pip install -r requirements_test.txt
pytest
ruff check custom_components tests scripts
```

Tests run against a real Home Assistant (`pytest-homeassistant-custom-component`) for the setup, entities and options flow, and against mocks for the coordinator's logic.

## Card

The card's sources live in `frontend/`; run the commands from there (Node 24):

```bash
npm ci
npm run build      # writes ../custom_components/homeshift/www/homeshift-card.js
npm run typecheck
npm run lint
npm test
```

Commit the rebuilt bundle with the sources: CI fails when it differs from a fresh build. The integration serves that file under `/homeshift/homeshift-card.js` and loads it in every dashboard (`custom_components/homeshift/frontend.py`); after a build, reload the browser page.

The card is documented for users in [The card](card.md).

## Devcontainer

**Dev Containers: Reopen in Container** in VS Code starts a Home Assistant on http://localhost:8123 with HomeShift, the Scheduler integration and its card, sample schedules, simulated covers, an outdoor temperature and two simulated auto start/stop switches. `./container restart` restarts Home Assistant.

## Continuous integration

- **Tests**: pytest
- **Validate**: hassfest, HACS, ruff, the card (typecheck, lint, tests, build, bundle up to date)

## Documentation

The documentation exists in English (`docs/en/`) and French (`docs/fr/`), with the same pages; change both. The card screenshots (`docs/images/card/en/` and `fr/`) are the card rendered with simulated data, in each language. The screenshots of the options dialog (`docs/images/options/en/` and `fr/`) are taken in the devcontainer, once with the test user's profile language in English and once in French; the day mode names stay in French there because the test instance was set up in French.
