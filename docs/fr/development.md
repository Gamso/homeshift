# Développement

[← Documentation](../../README.fr.md#documentation) · [English](../en/development.md)

## Organisation du dépôt

```
custom_components/homeshift/   L'intégration
  www/homeshift-card.js        Le bundle de la carte, construit depuis frontend/ (non commité)
frontend/                      Les sources de la carte (TypeScript, Lit), voir frontend/README.md
tests/                         Les tests de l'intégration (pytest)
docs/                          Cette documentation (en/, fr/, images/)
.devcontainer/, container,     Un Home Assistant pour essayer, avec des entités simulées
scripts/
```

## Intégration

Python 3.14.2 ou plus récent, Home Assistant 2026.11 ou plus récent.

```bash
pip install -r requirements_test.txt
pytest
ruff check custom_components tests scripts
```

Les tests tournent sur un vrai Home Assistant (`pytest-homeassistant`) pour l'installation, les entités et l'options flow, et sur des simulations pour la logique du coordinateur.

## Carte

Les sources de la carte sont dans `frontend/` ; lancez les commandes depuis ce dossier (Node 24) :

```bash
npm ci
npm run build      # écrit ../custom_components/homeshift/www/homeshift-card.js
npm run typecheck
npm run lint
npm test
```

Le bundle n'est pas commité : ne commitez que les sources. L'intégration sert ce fichier sous `/homeshift/homeshift-card.js` et le charge dans tous les tableaux de bord (`custom_components/homeshift/frontend.py`) ; après un build, rechargez la page du navigateur. Sans build, HomeShift fonctionne sans sa carte et l'indique dans le journal.

La carte est documentée pour les utilisateurs dans [La carte](card.md).

## Devcontainer

**Dev Containers: Reopen in Container** dans VS Code construit la carte, puis démarre un Home Assistant sur http://localhost:8123 avec HomeShift, l'intégration Scheduler et sa carte, des plannings d'exemple, des volets simulés, une température extérieure et deux interrupteurs d'auto start/stop simulés. `./container card` reconstruit la carte et `./container restart` redémarre Home Assistant.

## Intégration continue

- **Tests** : pytest
- **Validate** : hassfest, HACS, ruff, pyright, la carte (typecheck, lint, tests, build)
- **Release** : à la publication d'une release GitHub, construit la carte et y joint `homeshift.zip` (le contenu de `custom_components/homeshift/`, carte comprise). HACS installe cette archive (`zip_release` dans `hacs.json`). Il peut être lancé à la main sur un tag existant (*Run workflow*).

## Publier une version

Mettez la version dans `manifest.json`, fusionnez, puis publiez une release GitHub dont le tag est cette version : le workflow **Release** y joint `homeshift.zip`. Une release sans cette archive ne peut pas être installée par HACS.

## Documentation

La documentation existe en anglais (`docs/en/`) et en français (`docs/fr/`), avec les mêmes pages : modifiez les deux. Les captures de la carte (`docs/images/card/en/` et `fr/`) sont la carte rendue avec des données simulées, dans chaque langue. Les captures de la fenêtre d'options (`docs/images/options/en/` et `fr/`) sont prises dans le devcontainer, une fois avec la langue du profil de l'utilisateur de test en anglais et une fois en français ; les noms des modes du jour y restent en français, car l'instance de test a été configurée en français.
