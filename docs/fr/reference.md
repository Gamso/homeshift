# Entités et services

[← Documentation](../../README.fr.md#documentation) · [English](../en/reference.md)

Les identifiants des entités ne dépendent pas de la langue de Home Assistant : une installation française a aussi `select.homeshift_day_mode`, seuls les noms affichés sont traduits. (Les identifiants sont donnés à la création d'une entité ; un identifiant que vous avez renommé est conservé.)

Certaines entités n'existent que tant que leur fonction est configurée ; elles disparaissent quand on la retire.

| Entité | Existe quand |
| --- | --- |
| `select.homeshift_day_mode`, `select.homeshift_thermostat_mode` | Toujours |
| `number.homeshift_override_duration`, `number.homeshift_early_switch` | Toujours |
| `sensor.homeshift_next_mode`, `sensor.homeshift_next_mode_at` | Toujours |
| `sensor.homeshift_cover_open_time`, `sensor.homeshift_cover_close_time` | Au moins un volet géré |
| `binary_sensor.homeshift_covers_left_open` | Au moins un volet géré |
| `button.homeshift_open_covers`, `button.homeshift_close_covers` | Au moins un volet géré |
| `sensor.homeshift_covers_inhibited` | Au moins un volet piloté (géré ou protégé) |
| `binary_sensor.homeshift_cover_heat_active` | Volets protégés et capteur de température réglés |
| `sensor.homeshift_auto_start_stop` | Au moins un équipement |

## Modes du jour

### `select.homeshift_day_mode`

Le [mode du jour](day-modes.md) en cours, réglé par le calendrier ou à la main.

- **Options :** `Maison`, `Travail`, `Télétravail`, `Absence` (`Home`, `Work`, `Remote`, `Away` en anglais)
- **Attributs :** `option_map`, `option_keys`, `current_key`, la clé du mode en cours quelle que soit la langue, et `calendar_error`, `{since: <heure ISO>}` tant qu'un calendrier est illisible et `null` sinon

### `select.homeshift_thermostat_mode`

Le mode thermostat en cours, voir [Plannings](schedulers.md#mode-thermostat).

- **Options :** `Eteint`, `Chauffage`, `Climatisation`, `Ventilation`
- **Attributs :** `option_map`, `option_keys`, `current_key`

### `number.homeshift_override_duration`

Combien de temps un mode choisi à la main est gardé avant que le calendrier reprenne la main (minutes, de 0 à 1440, par pas de 5, `0` = jusqu'au prochain passage du calendrier). Voir [Changer le mode à la main](day-modes.md#changer-le-mode-à-la-main).

### `number.homeshift_early_switch`

Combien de temps avant un événement horaire son mode commence (minutes, de 0 à 480, par pas de 5, `0` = désactivé). Voir [Bascule anticipée](day-modes.md#bascule-anticipée).

### `sensor.homeshift_next_mode`

Le prochain mode du jour. Quand aucun changement n'est prévu dans les 7 jours, le mode en cours.

### `sensor.homeshift_next_mode_at`

Quand commence le prochain mode (horodatage), bascule anticipée comprise.

## Volets

### `sensor.homeshift_cover_open_time`

L'heure d'ouverture du jour, `HH:MM`, ou `unknown` tant qu'elle n'est pas calculée.

### `sensor.homeshift_cover_close_time`

L'heure de fermeture du jour, `HH:MM`.

- **Attributs :** `sun_elevation`, l'élévation réglée, et `trigger` : `elevation`, ou `sunset` un jour où le soleil ne l'a pas atteinte

### `binary_sensor.homeshift_covers_left_open`

`on` quand la fermeture du soir a dû laisser des volets ouverts à cause d'une fenêtre ouverte (`device_class: problem`).

- **Attributs :** `covers` (ex. `["cover.volet_chambre"]`), `window_sensors` (le capteur qui a retenu chacun), `count`, `checked_on`
- Se remet à zéro quand les horaires du lendemain sont calculés, pas quand la fenêtre est fermée. Avec [Fermer dès que la fenêtre se referme](covers.md#fermer-dès-que-la-fenêtre-se-referme), un volet sort de la liste dès que HomeShift le ferme.
- Survit à un redémarrage.

Une notification quand des volets restent ouverts :

```yaml
automation:
  - alias: Volets restés ouverts
    triggers:
      - trigger: state
        entity_id: binary_sensor.homeshift_covers_left_open
        to: "on"
    actions:
      - action: notify.persistent_notification
        data:
          message: >
            Volets non fermés ce soir :
            {{ state_attr('binary_sensor.homeshift_covers_left_open', 'covers') | join(', ') }}
```

### `binary_sensor.homeshift_cover_heat_active`

`on` tant que les conditions de la [protection contre la chaleur](covers.md#protection-contre-la-chaleur) sont réunies : dans la plage du jour et température extérieure au-dessus du seuil (`device_class: heat`). `unknown` tant que les horaires du jour ne sont pas calculés, ou quand le capteur de température est indisponible.

### `button.homeshift_open_covers` / `button.homeshift_close_covers`

Ouvrent ou ferment les volets gérés tout de suite. Voir [Ouvrir et fermer à la demande](covers.md#ouvrir-et-fermer-à-la-demande). Une commande qui échoue est journalisée ; elle ne rend jamais les boutons indisponibles.

### `sensor.homeshift_covers_inhibited`

Le nombre de [volets en pause](covers.md#mettre-des-volets-en-pause).

- **Attributs :** `covers`, chaque volet en pause avec sa fin (`null` = jusqu'à reprise), ex. `{"cover.volet_chambre": "2026-10-12T08:00:00+02:00"}`, et `managed_covers`, tous les volets qui peuvent être mis en pause
- Une pause terminée disparaît à la synchronisation suivante (sous 5 minutes).

## Auto start/stop des équipements

### `sensor.homeshift_auto_start_stop`

Le nombre d'[équipements](climates.md) gardés en marche par leur consigne en ce moment.

- **Attribut** `climates`, une entrée par équipement :

| Clé | Signification |
| --- | --- |
| `switch` | L'interrupteur d'auto start/stop |
| `name` | Son nom, sans « Enable auto start/stop » |
| `driven` | Si HomeShift le pilote dans le mode thermostat en cours |
| `comfort` | Si sa consigne est du côté confort du seuil (`null` quand il n'est pas piloté) |
| `auto_start_stop` | L'état réel de l'interrupteur (`null` s'il est indisponible) |
| `manual` | L'interrupteur diffère de ce que HomeShift a réglé : basculé à la main |
| `setpoint` | La température de consigne du climate (`null` s'il n'en a pas) |
| `threshold` | Le seuil du mode thermostat en cours (`null` quand il n'est pas piloté) |
| `comfort_when` | `above` (chauffage) ou `below` (climatisation, ventilation) : le côté du seuil qui le garde en marche |

## Services

### `homeshift.sync_calendar`

Lit les calendriers tout de suite et met à jour le mode du jour si besoin (cela se fait aussi toutes les 5 minutes).

### `homeshift.refresh_schedulers`

Réapplique les [interrupteurs Scheduler](schedulers.md) des modes du jour et thermostat en cours.

### `homeshift.open_covers` / `homeshift.close_covers`

Comme les boutons ci-dessus. Aucun champ. Sans volet géré, ne fait rien (et journalise un avertissement). Les volets en pause ne sont pas touchés.

### `homeshift.inhibit_covers`

[Met en pause](covers.md#mettre-des-volets-en-pause) des volets.

| Champ | Obligatoire | Description |
| --- | :---: | --- |
| `entity_id` | ✅ | Les volets à mettre en pause. Seuls les volets pilotés par HomeShift sont acceptés. |
| `duration` | | Combien de temps, ex. `{"days": 3}` ou `"72:00:00"` |
| `until` | | Quand elle se termine, ex. `"2026-10-12 08:00:00"` (fuseau horaire de Home Assistant) |

Donnez `duration` ou `until` ; sans l'un ni l'autre, la pause dure jusqu'à la reprise. Rappeler le service sur un volet en pause remplace sa fin.

```yaml
action: homeshift.inhibit_covers
data:
  entity_id:
    - cover.volet_chambre
  duration:
    days: 3
```

### `homeshift.resume_covers`

Termine des pauses en avance. `entity_id` est optionnel : sans lui, tous les volets en pause reprennent.

## Diagnostics

**Télécharger les diagnostics**, sur la page de l'intégration, rassemble la configuration, les données du coordinateur et les horaires des volets du jour, pour un rapport de bug.
