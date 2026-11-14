# HomeShift card — sources

The dashboard card of the [HomeShift integration](../README.md), in TypeScript with [Lit](https://lit.dev). What it shows and its options are documented in [docs/en/card.md](../docs/en/card.md) ([français](../docs/fr/card.md)).

The integration ships the built card: nothing here needs to be installed in Home Assistant.

## Commands

Run them from this folder (Node 24):

```bash
npm ci
npm run build      # writes ../custom_components/homeshift/www/homeshift-card.js
npm run typecheck
npm run lint
npm test
```

The bundle is not committed: the **Release** workflow builds it and ships it in the release archive (`homeshift.zip`).

## Layout

```
src/
  index.ts                     Registers the card in the card picker
  types.ts                     Card configuration and the table of entity options
  components/
    homeshift-card.ts          The card
    homeshift-card-editor.ts   Its visual editor
  schedule/                    The schedules panel and its 24 h timelines
  localize/                    Translations (en, fr)
  state.ts, time.ts            Entity state and time formatting helpers
test/                          Vitest tests (happy-dom)
```

Conventions for changes are in [AGENTS.md](AGENTS.md). More on developing HomeShift in [docs/en/development.md](../docs/en/development.md).
