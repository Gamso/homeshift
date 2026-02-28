# User Guide: Configuring Schedulers for Thermostat Modes

## Overview

With this update, thermostat modes are now **fixed** and cannot be modified. The four modes are:
- **Eteint** (Off)
- **Chauffage** (Heating)
- **Climatisation** (Air Conditioning)
- **Ventilation** (Ventilation)

You can now **associate one or more scheduler switches** with each mode.

## How to Configure

### Initial Setup

When you first add the Day Mode integration:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "HomeShift"
4. Fill in the configuration form:
   - **Work Calendar Entity**: Select your work calendar
   - **Holiday Calendar Entity**: (Optional) Select holiday calendar
   - **Day Modes**: Leave default or customize (e.g., "Maison, Travail, Télétravail, Absence")
   - **Daily Check Time**: Time to check next day (default: 00:10:00)

**Note:** You will NOT see a "Thermostat Modes" field - these are now fixed.

### Configuring Schedulers

After initial setup, configure schedulers for each thermostat mode:

1. Go to **Settings** → **Devices & Services**
2. Find **Day Mode** integration
3. Click **Configure** (three dots → Configure)
4. You will see the configuration form with these fields:

#### General Settings
- **Work Calendar Entity**
- **Holiday Calendar Entity**
- **Day Modes**
- **Daily Check Time**

#### Scheduler Configuration (NEW!)
- **Schedulers for 'Eteint' mode**: Select switch entities
- **Schedulers for 'Chauffage' mode**: Select switch entities
- **Schedulers for 'Climatisation' mode**: Select switch entities
- **Schedulers for 'Ventilation' mode**: Select switch entities

Each field allows you to select **multiple switch entities**.

### Example Configuration

Let's say you have these scheduler switches:
- `switch.scheduler_heating_morning`
- `switch.scheduler_heating_evening`
- `switch.scheduler_cooling_afternoon`
- `switch.scheduler_cooling_night`
- `switch.scheduler_vent_continuous`

You can configure them like this:

**Eteint mode**: (no schedulers)
- Leave empty - nothing should run when thermostat is off

**Chauffage mode**: (heating schedulers)
- Select: `switch.scheduler_heating_morning`
- Select: `switch.scheduler_heating_evening`

**Climatisation mode**: (cooling schedulers)
- Select: `switch.scheduler_cooling_afternoon`
- Select: `switch.scheduler_cooling_night`

**Ventilation mode**: (ventilation schedulers)
- Select: `switch.scheduler_vent_continuous`

### How It Works

Once configured, when you change the thermostat mode (using the "Mode Thermostat" entity or automation):

1. Day Mode will automatically:
   - **Turn ON** the schedulers associated with the current mode
   - **Turn OFF** the schedulers associated with other modes

2. This happens:
   - When you manually change the mode
   - When you call the `day_mode.refresh_schedulers` service
   - During automated mode changes

### Example Automation

```yaml
automation:
  - alias: "Sync schedulers when mode changes"
    trigger:
      - platform: state
        entity_id: select.mode_thermostat
    action:
      - service: day_mode.refresh_schedulers
```

## Tips

### Naming Your Schedulers

It's helpful to name your scheduler switches clearly:
- `switch.scheduler_heating_morning`
- `switch.scheduler_heating_evening`
- `switch.scheduler_cooling_day`
- `switch.scheduler_cooling_night`

This makes it easy to identify which scheduler does what.

### Using Multiple Schedulers

You can have multiple schedulers per mode for different purposes:
- Morning vs evening schedules
- Weekday vs weekend schedules
- Different rooms or zones

### Testing Your Configuration

After configuring schedulers:

1. Manually change the thermostat mode: 
   - Go to the "Mode Thermostat" entity
   - Select a different mode

2. Call the refresh service:
   ```yaml
   service: day_mode.refresh_schedulers
   ```

3. Check that the correct schedulers are turned on/off

## Frequently Asked Questions

### Q: Can I change the thermostat mode names?
**A:** No, the four modes are now fixed and cannot be changed. This ensures consistency across the integration.

### Q: What if I don't want to use all four modes?
**A:** That's fine! Just leave the scheduler fields empty for modes you don't use.

### Q: Can I have the same scheduler in multiple modes?
**A:** Technically yes, but it's not recommended as it may cause confusion about when the scheduler should be active.

### Q: What if I update my schedulers later?
**A:** Just go back to the configuration (Configure button) and update the scheduler selections. The changes take effect immediately.

### Q: Do I need to configure schedulers for the integration to work?
**A:** No, scheduler configuration is optional. The integration will work without it, but the `refresh_schedulers` service won't do anything.

## Migration from Previous Version

If you were using the old version where thermostat modes were configurable:

1. Your existing thermostat modes will be automatically converted to the fixed values
2. You'll need to configure scheduler associations (they don't automatically migrate)
3. Previous functionality continues to work normally

## Support

For issues or questions, please file an issue on the GitHub repository:
https://github.com/Gamso/day_mode/issues
