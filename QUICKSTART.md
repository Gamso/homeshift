# Quick Start Guide - Day Mode

## Installation rapide

### Option 1: Installation via HACS (recommandé)

1. Ouvrez HACS dans Home Assistant
2. Cliquez sur "Integrations"
3. Cliquez sur le menu (3 points) en haut à droite
4. Sélectionnez "Custom repositories"
5. Ajoutez : `https://github.com/Gamso/day_mode`
6. Catégorie : `Integration`
7. Recherchez "Day Mode" et installez
8. Redémarrez Home Assistant

### Option 2: Installation manuelle

```bash
cd /config/custom_components
git clone https://github.com/Gamso/day_mode.git day_mode_temp
mv day_mode_temp/custom_components/day_mode ./
rm -rf day_mode_temp
```

Redémarrez Home Assistant.

## Configuration initiale

1. Allez dans **Configuration** → **Intégrations**
2. Cliquez sur **+ Ajouter une intégration**
3. Recherchez **"Day Mode"**
4. Configurez :
   - **Calendrier Travail** : `calendar.travail` (votre calendrier de travail)
   - **Calendrier Jours Fériés** : `calendar.jours_feries_et_autres_fetes_en_france` (optionnel)
   - **Modes de Jour** : `Maison, Travail, Télétravail, Absence` (par défaut)
   - **Modes Thermostat** : `Eteint, Chauffage, Climatisation, Ventilation` (par défaut)
   - **Heure de Vérification** : `00:10:00` (par défaut)

## Première utilisation

### 1. Vérifiez les entités créées

Allez dans **Outils de développement** → **États** et recherchez :
- `select.mode_jour`
- `select.mode_thermostat`
- `sensor.next_day_type`

### 2. Testez les modes

Changez manuellement les modes depuis l'interface :
1. Ouvrez l'entité `select.mode_jour`
2. Sélectionnez un mode (ex: "Maison")
3. Vérifiez que le changement est pris en compte

### 3. Créez votre première automatisation

```yaml
automation:
  - alias: "Test Day Mode"
    trigger:
      - platform: state
        entity_id: select.mode_jour
    action:
      - service: notify.persistent_notification
        data:
          message: "Mode jour changé en {{ states('select.mode_jour') }}"
```

### 4. Configurez vos calendriers

Pour que la détection automatique fonctionne, créez des événements dans votre calendrier :
- Événement "Vacances" → Mode "Maison"
- Événement "Télétravail" → Mode "Télétravail"
- Week-end → Mode "Maison" (automatique)
- Jour férié → Mode "Maison" (si calendrier configuré)

## Exemple complet

### 1. Créez des schedulers (via Scheduler Component)

Installez [Scheduler Component](https://github.com/nielsfaber/scheduler-component) et créez des schedulers :
- `switch.schedulers_chauffage_maison`
- `switch.schedulers_chauffage_travail`
- `switch.schedulers_chauffage_teletravail`

### 2. Créez l'automatisation de gestion

```yaml
automation:
  - alias: "Gestion automatique des schedulers"
    trigger:
      - platform: state
        entity_id: select.mode_jour
      - platform: state
        entity_id: select.mode_thermostat
    action:
      - service: day_mode.refresh_schedulers
```

### 3. Ajoutez au dashboard

```yaml
type: entities
title: Gestion Maison
entities:
  - entity: select.mode_jour
  - entity: select.mode_thermostat
  - entity: sensor.next_day_type
```

## Dépannage

### Les entités n'apparaissent pas

1. Vérifiez les logs : **Configuration** → **Logs**
2. Recherchez les erreurs liées à `day_mode`
3. Redémarrez Home Assistant

### Le mode ne change pas automatiquement

1. Vérifiez que le calendrier est configuré
2. Vérifiez que les événements sont bien nommés "Vacances" ou "Télétravail"
3. Attendez 00:10 ou appelez manuellement `day_mode.check_next_day`

### Les schedulers ne se rafraîchissent pas

1. Vérifiez que vos schedulers suivent la convention de nommage
2. Créez une automatisation manuelle pour tester
3. Appelez manuellement `day_mode.refresh_schedulers`

## Prochaines étapes

- Consultez [EXAMPLES.md](EXAMPLES.md) pour plus d'exemples
- Lisez [README.md](README.md) pour la documentation complète
- Contribuez via [CONTRIBUTING.md](CONTRIBUTING.md)

## Support

Besoin d'aide ?
- 🐛 [Signaler un bug](https://github.com/Gamso/day_mode/issues)
- 💡 [Demander une fonctionnalité](https://github.com/Gamso/day_mode/issues)
- 📖 [Consulter la documentation](https://github.com/Gamso/day_mode)
