# Intégration des Calendriers par Défaut dans Home Assistant

## Vue d'ensemble

Les calendriers sont automatiquement intégrés et peuplés au démarrage de Home Assistant via :

1. **Fichiers ICS locaux** (`calendars/*.ics`) - source des données
2. **Automations** (`config/automations/calendars.yaml`) - charge les événements au démarrage
3. **Script d'initialisation** (`scripts/init_calendars.py`) - crée les calendriers locaux
4. **Tests automatiques** (`tests/test_calendars.py`) - valide la configuration

## Architecture

```
calendars/
├── teletravail.ics          ← Données brutes (récurrent + vacances)
└── jours_feries_fr.ics       ← Données brutes (11 jours fériés)
         ↓
config/www/calendars/        ← Copie accessible via HTTP (HA)
         ↓
config/automations/calendars.yaml  ← Crée les événements au démarrage
         ↓
Home Assistant Local Calendars
```

## Mise en place complète (Step-by-Step)

### Étape 1 : Vérifier que les fichiers ICS existent

```bash
ls -la calendars/
ls -la config/www/calendars/
```

### Étape 2 : Créer les calendriers locaux

**Option A : Via l'UI (simple)**
1. Ouvrir **Paramètres** → **Appareils et services**
2. Cliquer sur **Ajouter une intégration**
3. Chercher **"Local Calendar"**
4. Créer deux calendriers :
   - Nom : "Télétravail"
   - Nom : "Jours fériés"

**Option B : Via script Python (automatisé)**

D'abord, obtenir un token d'authentification long terme :
1. Aller dans **Paramètres** → **Développement** → **Jetons d'accès**
2. Créer un nouveau token (copier le texte complet)

Puis exécuter le script :
```bash
python scripts/init_calendars.py http://localhost:8123 <votre_token>
```

Exemple :
```bash
python scripts/init_calendars.py http://localhost:8123 eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Ou vérifier seulement sans créer :
```bash
python scripts/init_calendars.py http://localhost:8123 <token> --check-only
```

### Étape 3 : Redémarrer Home Assistant

Les automations se déclencheront au prochain démarrage et rempliront les calendriers.

**Depuis l'UI :** Paramètres → Système → Redémarrer

**Depuis le terminal :**
```bash
./container restart
```

### Étape 4 : Vérifier dans l'UI

- Ouvrir le **Calendrier** dans la barre latérale
- Vous devriez voir :
  - Les **mardis** marqués "Télétravail"
  - Les **périodes de vacances** (printemps, été, Noël)
  - Les **11 jours fériés** français

## Configuration détaillée

### Automations (`config/automations/calendars.yaml`)

Deux automations déclenchées au démarrage de Home Assistant :

1. **`day_mode_init_calendars`** → Appelle les scripts de chargement
2. **Scripts** → Creatent les événements via `calendar.create_event`

Les événements sont créés avec `continue_on_error: true` pour éviter les erreurs si les calendriers n'existent pas (au 1er démarrage).

### Fichiers ICS

**Télétravail** (`teletravail.ics`) :
- ✅ Récurrence RRULE : Tous les mardis (FREQ=WEEKLY;BYDAY=TU)
- ✅ 3 périodes de vacances (printemps, été, Noël)

**Jours fériés** (`jours_feries_fr.ics`) :
- ✅ 11 jours fériés français 2026
- ✅ Chaînes UTF-8 (accents conservés)

## Accès aux calendriers

### Via la barre latérale Home Assistant
- **Calendrier** → Affiche tous les événements

### Via l'API Home Assistant

**Récupérer les événements entre deux dates :**
```bash
curl -X POST http://localhost:8123/api/calendars/calendar.teletravail/events \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date_time": "2026-01-01T00:00:00",
    "end_date_time": "2026-02-01T00:00:00"
  }'
```

### Via l'intégration Calendar (automations)

```yaml
automation:
  - id: test_calendar
    trigger:
      platform: calendar
      entity_id: calendar.teletravail
      event: start
    action:
      - action: notify.notify
        data:
          message: "Télétravail commence aujourd'hui !"
```

## Tests

Valider la configuration :

```bash
# Tests complets
pytest tests/test_calendars.py -v

# Seulement les tests basiques (sans icalendar)
pytest tests/test_calendars.py::TestCalendarsBasic -v

# Avec couverture
pytest tests/test_calendars.py --cov=calendars
```

## Dépannage

### Les événements ne s'affichent pas après redémarrage

1. **Vérifier que les calendriers existent** :
   ```bash
   python scripts/init_calendars.py http://localhost:8123 <token> --check-only
   ```

2. **Vérifier les logs Home Assistant** :
   - Paramètres → Logs → Chercher "day_mode"

3. **Forcer l'exécution de l'automation** :
   - Paramètres → Automations et scènes
   - Chercher "Day Mode - Initialiser"
   - Cliquer ⋮ → Déclencher

### S'il manque certains événements

- Les périodes multi-jours sont créées avec `start_date`/`end_date` (journées entières)
- Les événements récurrents ne sont pas directement supportés via `calendar.create_event` → créer un événement sur le 1er mardi, puis dupliquer manuellement ou via automation supplémentaire

### Les ICS ne se chargent pas

- Vérifier que `config/www/calendars/*.ics` existent
- Vérifier les permissions de lecture
- Vérifier que l'URL locale est accessible : `http://localhost:8123/local/calendars/teletravail.ics`

## Intégrations futures possibles

- 🔄 Synchronisation bidirectionnelle avec Google Calendar
- 📱 Synchronisation avec Nextcloud Calendar (CalDAV)
- 🔔 Notifications avant les événements (15 min avant par défaut)
- 📊 Dashboard affichant les jours télétravail restants
- 🌐 Export en format iCal pour partage

## Ressources

- [Home Assistant Calendar Integration](https://www.home-assistant.io/integrations/calendar/)
- [Local Calendar Integration](https://www.home-assistant.io/integrations/local_calendar/)
- [REST API - Calendars](https://developers.home-assistant.io/docs/api/rest/)
- [iCalendar Format (RFC 5545)](https://datatracker.ietf.org/doc/html/rfc5545)
