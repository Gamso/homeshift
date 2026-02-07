# Exemples d'automatisations pour Day Mode

## Automatisation basique

Cette automatisation rafraîchit automatiquement les schedulers quand le mode change :

```yaml
automation:
  - alias: "Rafraîchir schedulers au changement de mode"
    description: "Active les bons schedulers en fonction de mode_jour et mode_thermostat"
    trigger:
      - platform: state
        entity_id: select.mode_thermostat
      - platform: state
        entity_id: select.mode_jour
    action:
      - service: day_mode.refresh_schedulers
```

## Automatisation avec gestion des schedulers

Cette automatisation gère manuellement les schedulers (si vous préférez ne pas utiliser la logique intégrée) :

```yaml
automation:
  - alias: "Gestion complète des schedulers"
    description: "Active les bons schedulers en fonction des modes"
    trigger:
      - platform: state
        entity_id: select.mode_thermostat
      - platform: state
        entity_id: select.mode_jour
    action:
      # Désactiver tous les schedulers
      - service: switch.turn_off
        target:
          entity_id:
            - switch.schedulers_chauffage_absence
            - switch.schedulers_chauffage_maison
            - switch.schedulers_chauffage_travail
            - switch.schedulers_chauffage_teletravail
            - switch.schedule_climatisation_absence_salon
            - switch.schedule_climatisation_maison_salon
            - switch.schedule_climatisation_travail_salon
            - switch.schedule_climatisation_teletravail_salon
      
      # Activer les schedulers correspondants
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ states('select.mode_thermostat') == 'Chauffage' }}"
            sequence:
              - service: switch.turn_on
                target:
                  entity_id: >
                    {% set mode = states('select.mode_jour') | lower | replace('é','e') %}
                    switch.schedulers_chauffage_{{ mode }}
          
          - conditions:
              - condition: template
                value_template: "{{ states('select.mode_thermostat') == 'Climatisation' }}"
            sequence:
              - service: switch.turn_on
                target:
                  entity_id: >
                    {% set mode = states('select.mode_jour') | lower | replace('é','e') %}
                    switch.schedule_climatisation_{{ mode }}_salon
```

## Automatisation avec contrôle des thermostats

Cette automatisation contrôle également les entités climate :

```yaml
automation:
  - alias: "Contrôle thermostat et schedulers"
    description: "Gère les thermostats et schedulers selon les modes"
    trigger:
      - platform: state
        entity_id: select.mode_thermostat
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: select.mode_thermostat
                state: "Chauffage"
            sequence:
              - service: climate.set_hvac_mode
                target:
                  entity_id:
                    - climate.bureau
                    - climate.chambre
                    - climate.salon
                data:
                  hvac_mode: heat
          
          - conditions:
              - condition: state
                entity_id: select.mode_thermostat
                state: "Climatisation"
            sequence:
              - service: climate.set_hvac_mode
                target:
                  entity_id:
                    - climate.salon
                data:
                  hvac_mode: cool
              - service: climate.turn_off
                target:
                  entity_id:
                    - climate.bureau
                    - climate.chambre
          
          - conditions:
              - condition: state
                entity_id: select.mode_thermostat
                state: "Eteint"
            sequence:
              - service: climate.turn_off
                target:
                  entity_id:
                    - climate.bureau
                    - climate.chambre
                    - climate.salon
```

## Notification du changement de mode

Cette automatisation envoie une notification quand le mode change :

```yaml
automation:
  - alias: "Notification changement de mode"
    description: "Envoie une notification quand le mode jour change"
    trigger:
      - platform: state
        entity_id: select.mode_jour
    action:
      - service: notify.mobile_app
        data:
          message: "Mode jour changé en {{ states('select.mode_jour') }}"
          title: "Day Mode"
```

## Vérification manuelle du lendemain

Bouton pour vérifier manuellement le type de lendemain :

```yaml
script:
  check_tomorrow:
    alias: "Vérifier le type de lendemain"
    sequence:
      - service: day_mode.check_next_day
```

## Dashboard Lovelace

Exemple de carte Lovelace pour contrôler Day Mode :

```yaml
type: entities
title: Day Mode
entities:
  - entity: select.mode_jour
    name: Mode Jour
  - entity: select.mode_thermostat
    name: Mode Thermostat
  - entity: sensor.next_day_type
    name: Type du Lendemain
  - type: button
    name: Vérifier le lendemain
    tap_action:
      action: call-service
      service: day_mode.check_next_day
  - type: button
    name: Rafraîchir schedulers
    tap_action:
      action: call-service
      service: day_mode.refresh_schedulers
```
