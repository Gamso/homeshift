# Installation Guide - Day Mode

Guide détaillé d'installation et de configuration du composant Day Mode pour Home Assistant.

## Prérequis

- Home Assistant Core 2023.1.0 ou supérieur
- Accès au dossier `custom_components` de votre installation Home Assistant
- (Optionnel) HACS installé
- (Optionnel) Un calendrier configuré dans Home Assistant

## Méthode 1 : Installation via HACS (Recommandé)

### Étape 1 : Ajouter le repository

1. Ouvrez HACS dans votre installation Home Assistant
2. Cliquez sur **Integrations**
3. Cliquez sur le menu ⋮ (trois points) en haut à droite
4. Sélectionnez **Custom repositories**
5. Dans le champ "Repository", entrez : `https://github.com/Gamso/day_mode`
6. Dans "Category", sélectionnez : **Integration**
7. Cliquez sur **Add**

### Étape 2 : Installer le composant

1. Recherchez "Day Mode" dans HACS
2. Cliquez sur **Download**
3. Sélectionnez la dernière version
4. Cliquez sur **Download**

### Étape 3 : Redémarrer Home Assistant

1. Allez dans **Configuration** → **Server Controls**
2. Cliquez sur **Restart** (ou **Redémarrer**)
3. Attendez que Home Assistant redémarre

## Méthode 2 : Installation Manuelle

### Étape 1 : Télécharger les fichiers

#### Option A : Via Git (recommandé)

```bash
cd /config  # ou le chemin de votre configuration Home Assistant
mkdir -p custom_components
cd custom_components
git clone https://github.com/Gamso/day_mode.git day_mode_temp
mv day_mode_temp/custom_components/day_mode ./
rm -rf day_mode_temp
```

#### Option B : Téléchargement manuel

1. Téléchargez la dernière version depuis [GitHub Releases](https://github.com/Gamso/day_mode/releases)
2. Extrayez l'archive
3. Copiez le dossier `custom_components/day_mode` dans votre dossier `custom_components`

### Étape 2 : Vérifier l'installation

Votre structure de fichiers doit ressembler à :
```
config/
├── custom_components/
│   └── day_mode/
│       ├── __init__.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── manifest.json
│       ├── select.py
│       ├── sensor.py
│       ├── services.yaml
│       ├── strings.json
│       └── translations/
│           ├── en.json
│           └── fr.json
└── configuration.yaml
```

### Étape 3 : Redémarrer Home Assistant

Redémarrez Home Assistant pour charger le nouveau composant.

## Configuration

### Étape 1 : Ajouter l'intégration

1. Allez dans **Configuration** → **Intégrations**
2. Cliquez sur **+ Ajouter une intégration** (en bas à droite)
3. Recherchez **"Day Mode"**
4. Cliquez sur **Day Mode** dans les résultats

### Étape 2 : Configuration initiale

Remplissez le formulaire de configuration :

#### Calendrier Travail (Requis)
- Sélectionnez l'entité calendrier contenant vos événements de travail
- Exemple : `calendar.travail`
- Si vous n'avez pas de calendrier, vous pouvez en créer un via l'intégration CalDAV ou Google Calendar

#### Calendrier Jours Fériés (Optionnel)
- Sélectionnez l'entité calendrier des jours fériés
- Exemple : `calendar.jours_feries_et_autres_fetes_en_france`
- Laissez vide si vous n'utilisez pas cette fonctionnalité

#### Modes de Jour (Optionnel)
- Liste des modes de jour séparés par des virgules
- Par défaut : `Maison, Travail, Télétravail, Absence`
- Vous pouvez personnaliser selon vos besoins
- Exemples :
  - `Home, Work, Remote, Away` (en anglais)
  - `Casa, Trabajo, Teletrabajo, Ausencia` (en espagnol)

#### Modes Thermostat (Optionnel)
- Liste des modes thermostat séparés par des virgules
- Par défaut : `Eteint, Chauffage, Climatisation, Ventilation`
- Personnalisez selon votre installation

#### Heure de Vérification (Optionnel)
- Heure de la vérification quotidienne au format HH:MM:SS
- Par défaut : `00:10:00` (minuit dix)
- C'est à cette heure que le système vérifie le type du lendemain

### Étape 3 : Finaliser

Cliquez sur **Soumettre** pour terminer la configuration.

## Vérification de l'installation

### Vérifier les entités créées

1. Allez dans **Outils de développement** → **États**
2. Recherchez les entités suivantes :
   - `select.mode_jour` : Sélecteur du mode de jour
   - `select.mode_thermostat` : Sélecteur du mode thermostat
   - `sensor.next_day_type` : Type du lendemain

### Vérifier les services

1. Allez dans **Outils de développement** → **Services**
2. Recherchez les services suivants :
   - `day_mode.refresh_schedulers`
   - `day_mode.check_next_day`

### Tester un changement de mode

1. Allez dans **Configuration** → **Intégrations**
2. Trouvez **Day Mode** et cliquez dessus
3. Cliquez sur une entité (par exemple `select.mode_jour`)
4. Changez la valeur et vérifiez qu'elle se met à jour

## Configuration des calendriers

Pour que la détection automatique fonctionne, configurez vos calendriers :

### Calendrier de travail

Créez des événements avec les titres suivants :
- **"Vacances"** : Force le mode "Maison"
- **"Télétravail"** : Force le mode "Télétravail"

### Calendrier des jours fériés

Utilisez un calendrier existant ou créez-en un avec les jours fériés de votre pays.

## Prochaines étapes

1. Consultez [QUICKSTART.md](QUICKSTART.md) pour un guide de démarrage rapide
2. Lisez [EXAMPLES.md](EXAMPLES.md) pour des exemples d'automatisations
3. Configurez vos schedulers et automatisations

## Dépannage

### L'intégration n'apparaît pas

- Vérifiez que les fichiers sont bien dans `custom_components/day_mode`
- Redémarrez Home Assistant
- Vérifiez les logs dans **Configuration** → **Logs**

### Erreur lors de la configuration

- Vérifiez que les entités calendrier existent
- Vérifiez le format des modes (séparés par des virgules)
- Vérifiez le format de l'heure (HH:MM:SS)

### Les entités ne se créent pas

- Vérifiez les logs pour les erreurs
- Supprimez et recréez l'intégration
- Redémarrez Home Assistant

## Support

Pour toute question ou problème :
- 📖 [Documentation complète](README.md)
- 🐛 [Signaler un bug](https://github.com/Gamso/day_mode/issues)
- 💬 [Discussions](https://github.com/Gamso/day_mode/discussions)
