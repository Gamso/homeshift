# Day Mode - Home Assistant Custom Component

Un composant personnalisé pour Home Assistant qui gère automatiquement les modes de jour et les modes de thermostat en fonction d'un calendrier.

## Description

Ce composant permet de :
1. Récupérer les événements d'un agenda pour connaître le type de jour du lendemain : Maison, Travail, Télétravail, Absence
2. Piloter les schedulers (activer/désactiver) en fonction du type de jour et du mode thermostat

## Fonctionnalités

- **Détection automatique du type de jour** : Basé sur les événements du calendrier, les week-ends et les jours fériés
- **Modes de jour configurables** : Maison, Travail, Télétravail, Absence (personnalisables)
- **Modes thermostat configurables** : Eteint, Chauffage, Climatisation, Ventilation (personnalisables)
- **Vérification quotidienne automatique** : Vérifie et met à jour le mode du lendemain à 00:10
- **Services Home Assistant** : Contrôle manuel via des services

## Installation

### HACS (Recommandé)

1. Ouvrez HACS dans Home Assistant
2. Allez dans "Integrations"
3. Cliquez sur le menu trois points en haut à droite
4. Sélectionnez "Custom repositories"
5. Ajoutez `https://github.com/Gamso/day_mode` comme repository
6. Sélectionnez "Integration" comme catégorie
7. Cliquez sur "Add"
8. Recherchez "HomeShift" et installez-le
9. Redémarrez Home Assistant

### Installation Manuelle

1. Téléchargez le dossier `custom_components/homeshift`
2. Copiez-le dans le dossier `custom_components` de votre configuration Home Assistant
3. Redémarrez Home Assistant

## Configuration

### Via l'interface utilisateur

1. Allez dans Configuration → Intégrations
2. Cliquez sur "+ Ajouter une intégration"
3. Recherchez "HomeShift"
4. Suivez les étapes de configuration :
   - **Calendrier Travail** : Sélectionnez l'entité calendrier contenant vos événements de travail
   - **Calendrier Jours Fériés** (Optionnel) : Sélectionnez l'entité calendrier des jours fériés
   - **Modes de Jour** : Liste des modes séparés par des virgules (par défaut: Maison, Travail, Télétravail, Absence)
   - **Modes Thermostat** : Liste des modes séparés par des virgules (par défaut: Eteint, Chauffage, Climatisation, Ventilation)
   - **Heure de Vérification** : Heure de la vérification quotidienne (par défaut: 00:10:00)

## Utilisation

### Entités créées

L'intégration crée les entités suivantes :

1. **select.mode_jour** : Sélecteur du mode de jour actuel
2. **select.mode_thermostat** : Sélecteur du mode thermostat actuel
3. **sensor.next_day_type** : Capteur indiquant le type du lendemain (Vacances, Télétravail, ou Aucun)

### Services

- **day_mode.refresh_schedulers** : Rafraîchit manuellement l'état des schedulers
- **day_mode.check_next_day** : Vérifie et met à jour manuellement le mode du lendemain

### Événements du calendrier

Le composant reconnaît les événements suivants dans le calendrier :
- **"Vacances"** : Force le mode "Maison"
- **"Télétravail"** : Force le mode "Télétravail"

### Logique de détection du lendemain

La priorité de détection est la suivante :
1. Vacances (événement calendrier)
2. Week-end (samedi ou dimanche)
3. Télétravail (événement calendrier)
4. Jour férié (calendrier des jours fériés)
5. Travail (par défaut)

Le mode n'est pas modifié automatiquement si le mode actuel est "Absence".

## Exemple d'automatisation

Pour utiliser le composant avec vos schedulers existants :

```yaml
automation:
  - alias: "Rafraîchir schedulers au changement de mode"
    trigger:
      - platform: state
        entity_id: select.mode_thermostat
      - platform: state
        entity_id: select.mode_jour
    action:
      - service: day_mode.refresh_schedulers
```

## Organisation des schedulers

Pour que le composant puisse gérer vos schedulers, organisez-les selon la convention de nommage :
- `switch.schedulers_chauffage_maison`
- `switch.schedulers_chauffage_travail`
- `switch.schedulers_chauffage_teletravail`
- `switch.schedulers_chauffage_absence`
- etc.

Vous pouvez également utiliser des tags sur vos schedulers correspondant aux modes de jour et de thermostat.

## Développement

### Prérequis

- Python 3.11+
- Home Assistant Core (version récente)

### Configuration du développement

#### Option 1: Dev Container (Recommandé)

Le projet inclut une configuration Dev Container pour Visual Studio Code :

```bash
# Cloner le repository
git clone https://github.com/Gamso/day_mode.git
cd day_mode

# Ouvrir dans VS Code
code .

# Appuyer sur F1 et sélectionner "Dev Containers: Reopen in Container"
```

La configuration Dev Container inclut :
- Home Assistant complet pour les tests
- Extensions VS Code pré-configurées
- Environnement Python configuré
- Accès à Home Assistant sur http://localhost:8123

Voir [.devcontainer/README.md](.devcontainer/README.md) pour plus de détails.

#### Option 2: Docker Compose

```bash
# Lancer avec Docker Compose depuis le dossier container
cd container
docker-compose up -d
```

### Structure du projet

```
custom_components/homeshift/
├── __init__.py           # Point d'entrée de l'intégration
├── config_flow.py        # Configuration via l'interface utilisateur
├── const.py              # Constantes
├── coordinator.py        # Coordinateur de données
├── manifest.json         # Métadonnées de l'intégration
├── select.py             # Entités select
├── sensor.py             # Entités sensor
├── services.yaml         # Définition des services
├── strings.json          # Chaînes de traduction
└── translations/
    ├── en.json          # Traductions anglaises
    └── fr.json          # Traductions françaises
```

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer de nouvelles fonctionnalités
- Soumettre des pull requests

## Licence

Ce projet est sous licence MIT.

## Auteur

Gamso - [@Gamso](https://github.com/Gamso)

## Inspiration

Ce projet s'inspire de [smart_fan_controller](https://github.com/Gamso/smart_fan_controller) pour l'environnement Docker et la structure du projet.
