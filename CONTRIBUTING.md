# Guide de Développement - Day Mode

## Configuration de l'environnement

### Prérequis

- Docker et Docker Compose
- Python 3.11+
- Git
- Visual Studio Code (recommandé pour Dev Container)

### Démarrage rapide

#### Option 1: Dev Container (Recommandé)

Le projet inclut une configuration complète pour VS Code Dev Containers :

1. Clonez le repository :
```bash
git clone https://github.com/Gamso/day_mode.git
cd day_mode
```

2. Ouvrez dans VS Code :
```bash
code .
```

3. Lorsque VS Code vous propose d'ouvrir dans un conteneur, acceptez.
   - Ou appuyez sur `F1` et sélectionnez "Dev Containers: Reopen in Container"

4. Le conteneur va automatiquement :
   - Installer Home Assistant
   - Configurer l'environnement de développement
   - Démarrer Home Assistant sur le port 8123

5. Accédez à Home Assistant :
   - URL: http://localhost:8123
   - Créez un compte lors de la première connexion

Voir [.devcontainer/README.md](.devcontainer/README.md) pour plus de détails sur le Dev Container.

#### Option 2: Docker Compose

Si vous préférez Docker Compose sans Dev Container :

```bash
cd container
docker-compose up -d
```

Accédez à Home Assistant :
- URL: http://localhost:8123
- Créez un compte lors de la première connexion

### Structure du projet

```
day_mode/
├── .devcontainer/                  # Configuration Dev Container
│   ├── devcontainer.json          # Config VS Code
│   ├── configuration.yaml         # Config Home Assistant
│   ├── scheduler.storage          # Stockage scheduler
│   └── README.md                  # Documentation Dev Container
├── container/                      # Configuration Docker
│   ├── docker-compose.yml         # Configuration Docker Compose
│   └── starts_ha.sh              # Script de démarrage HA
├── custom_components/day_mode/    # Code du composant
│   ├── __init__.py               # Point d'entrée
│   ├── config_flow.py            # Configuration UI
│   ├── const.py                  # Constantes
│   ├── coordinator.py            # Gestion des données
│   ├── manifest.json             # Métadonnées
│   ├── select.py                 # Entités select
│   ├── sensor.py                 # Entités sensor
│   ├── services.yaml             # Services
│   ├── strings.json              # Traductions
│   └── translations/             # Fichiers de traduction
├── config/                       # Configuration Home Assistant
├── README.md                     # Documentation
├── EXAMPLES.md                   # Exemples d'usage
└── CONTRIBUTING.md               # Ce fichier
```

## Développement

### Tests locaux

1. Vérifiez les logs :
```bash
docker logs -f day_mode_dev
```

2. Redémarrez Home Assistant après modification :
```bash
docker restart day_mode_dev
```

3. Vérifiez le code :
```bash
# Validation de la syntaxe Python
python -m py_compile custom_components/day_mode/*.py

# Vérification du JSON
python -m json.tool custom_components/day_mode/manifest.json
python -m json.tool custom_components/day_mode/strings.json
```

### Ajout de fonctionnalités

1. Créez une branche :
```bash
git checkout -b feature/ma-nouvelle-fonctionnalite
```

2. Développez votre fonctionnalité

3. Testez localement

4. Commitez vos changements :
```bash
git add .
git commit -m "Ajout de ma nouvelle fonctionnalité"
```

5. Poussez et créez une Pull Request :
```bash
git push origin feature/ma-nouvelle-fonctionnalite
```

## Architecture

### Coordinateur (coordinator.py)

Le coordinateur gère :
- L'état du mode jour et du mode thermostat
- La vérification quotidienne du lendemain
- Le rafraîchissement des données du calendrier

### Entités Select (select.py)

Deux entités select sont créées :
- `select.mode_jour` : Sélection du mode de jour
- `select.mode_thermostat` : Sélection du mode thermostat

### Entités Sensor (sensor.py)

Un capteur est créé :
- `sensor.next_day_type` : Type du lendemain (Vacances, Télétravail, Aucun)

### Services

Deux services sont disponibles :
- `day_mode.refresh_schedulers` : Rafraîchit les schedulers
- `day_mode.check_next_day` : Vérifie le type du lendemain

## Debugging

### Activation des logs de debug

Ajoutez dans `config/configuration.yaml` :
```yaml
logger:
  default: info
  logs:
    custom_components.day_mode: debug
```

### Inspection des entités

Utilisez l'outil "Outils de développement" → "États" dans Home Assistant pour inspecter les entités créées.

## Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

### Guidelines

- Suivez le style de code existant
- Commentez le code complexe
- Mettez à jour la documentation
- Testez vos changements

## Support

Pour toute question ou problème :
- Ouvrez une issue sur GitHub
- Consultez la documentation
- Vérifiez les issues existantes

## Ressources

- [Documentation Home Assistant](https://developers.home-assistant.io/)
- [Documentation des intégrations](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Guide des config flows](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
