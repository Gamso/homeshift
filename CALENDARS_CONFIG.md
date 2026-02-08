# Configuration des Agendas pour les Tests

## Fichiers créés

Deux calendriers ICS locaux ont été créés pour les tests :

### 1. Calendrier Télétravail (`calendars/teletravail.ics`)
- **Événement récurrent** : Télétravail tous les **mardis** (jusqu'à fin 2027)
- **Événements de vacances** :
  - Vacances de printemps : 13-26 avril 2026
  - Vacances d'été : 3-16 août 2026
  - Vacances de Noël : 21 décembre 2026 - 3 janvier 2027

### 2. Calendrier Jours fériés France (`calendars/jours_feries_fr.ics`)
Tous les jours fériés français 2026 :
- 1er janvier : Nouvel An
- 6 avril : Lundi de Pâques
- 1er mai : Fête du Travail
- 8 mai : Victoire 1945
- 14 mai : Ascension
- 25 mai : Lundi de Pentecôte
- 14 juillet : Fête Nationale
- 15 août : Assomption
- 1er novembre : Toussaint
- 11 novembre : Armistice 1918
- 25 décembre : Noël

## Configuration dans Home Assistant

### Option 1 : Via l'UI (recommandé)
1. Aller dans **Paramètres** → **Appareils et services** → **Ajouter une intégration**
2. Chercher **"ICS Calendar"** ou **"iCalendar"**
3. Ajouter les URLs suivantes :
   - Télétravail : `http://localhost:8123/local/calendars/teletravail.ics`
   - Jours fériés : `http://localhost:8123/local/calendars/jours_feries_fr.ics`

### Option 2 : Utiliser Local Calendar
1. Aller dans **Paramètres** → **Appareils et services** → **Ajouter une intégration**
2. Chercher **"Local Calendar"**
3. Créer 2 calendriers et importer les événements manuellement (ou via API)

## Tests Automatiques

Les tests automatiques sont disponibles dans `tests/test_calendars.py` :

```bash
# Exécuter les tests
pytest tests/test_calendars.py -v

# Ou via container
./container pytest tests/test_calendars.py
```

Les tests vérifient :
- La validité des fichiers ICS
- La présence des événements récurrents (télétravail le mardi)
- La présence des périodes de vacances
- Les 11 jours fériés français 2026
- La compatibilité avec l'intégration calendar de Home Assistant
