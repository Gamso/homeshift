# Day Mode

Gestion automatique des modes de jour et des schedulers pour Home Assistant.

## Fonctionnalités

- 🗓️ Détection automatique du type de jour (Maison, Travail, Télétravail, Absence)
- 📅 Intégration avec les calendriers Home Assistant
- 🌡️ Gestion des modes thermostat (Eteint, Chauffage, Climatisation, Ventilation)
- ⏰ Vérification quotidienne automatique
- 🔄 Rafraîchissement automatique des schedulers
- ⚙️ Configuration via l'interface utilisateur

## Installation

1. Installez via HACS ou copiez manuellement le dossier `custom_components/day_mode`
2. Redémarrez Home Assistant
3. Allez dans Configuration → Intégrations
4. Cliquez sur "+ Ajouter une intégration"
5. Recherchez "Day Mode"

## Configuration

Lors de la configuration, vous devrez fournir :
- L'entité calendrier de travail
- L'entité calendrier des jours fériés (optionnel)
- Les modes de jour (par défaut: Maison, Travail, Télétravail, Absence)
- Les modes thermostat (par défaut: Eteint, Chauffage, Climatisation, Ventilation)

## Documentation complète

Pour plus d'informations, consultez le [README](https://github.com/Gamso/day_mode/blob/main/README.md).
