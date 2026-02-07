# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [1.0.0] - 2026-02-07

### Ajouté
- Création initiale du composant Day Mode
- Configuration via l'interface utilisateur (config flow)
- Entité `select.mode_jour` pour sélectionner le mode de jour
- Entité `select.mode_thermostat` pour sélectionner le mode thermostat
- Entité `sensor.next_day_type` pour afficher le type du lendemain
- Service `day_mode.refresh_schedulers` pour rafraîchir les schedulers
- Service `day_mode.check_next_day` pour vérifier le type du lendemain
- Détection automatique du type de jour basée sur :
  - Les événements du calendrier (Vacances, Télétravail)
  - Les week-ends
  - Les jours fériés (via calendrier optionnel)
- Vérification quotidienne automatique à 00:10
- Support des modes de jour personnalisables
- Support des modes thermostat personnalisables
- Traductions en français et anglais
- Documentation complète (README, QUICKSTART, EXAMPLES, CONTRIBUTING)
- Configuration Docker pour le développement
- Script de validation

### Fonctionnalités prévues pour les prochaines versions
- Gestion automatique des schedulers via tags
- Contrôle automatique des entités climate
- Interface de configuration des associations scheduler/mode
- Historique des changements de mode
- Statistiques d'utilisation
- Support de plus de types d'événements calendrier
- Notifications personnalisables

[1.0.0]: https://github.com/Gamso/day_mode/releases/tag/v1.0.0
