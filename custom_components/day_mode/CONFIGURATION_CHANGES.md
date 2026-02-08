# Configuration Changes: Fixed Thermostat Modes and Scheduler Association

## Summary

This update implements two key changes to the Day Mode integration:

1. **Thermostat modes are now fixed and cannot be modified by users**
2. **Users can now associate one or more scheduler switches with each thermostat mode**

## Changes Made

### 1. Fixed Thermostat Modes

**Files modified:**
- `custom_components/day_mode/const.py` - Added comment about backward compatibility
- `custom_components/day_mode/config_flow.py` - Removed thermostat_modes field from user configuration

**What changed:**
- Removed the `thermostat_modes` field from the initial configuration form
- Removed the `thermostat_modes` field from the options configuration form
- Thermostat modes are now hardcoded to: `["Eteint", "Chauffage", "Climatisation", "Ventilation"]`
- Users can no longer modify these values through the UI

### 2. Scheduler Configuration per Thermostat Mode

**New constant added:**
```python
CONF_SCHEDULERS_PER_MODE = "schedulers_per_mode"
```

**Configuration structure:**
The integration now stores scheduler associations in this format:
```python
{
    "schedulers_per_mode": {
        "Eteint": ["switch.scheduler_1", "switch.scheduler_2"],
        "Chauffage": ["switch.scheduler_heating_1", "switch.scheduler_heating_2"],
        "Climatisation": ["switch.scheduler_cooling_1"],
        "Ventilation": ["switch.scheduler_vent_1"]
    }
}
```

**UI changes:**
- In the options configuration form, users now see 4 additional fields:
  - "Schedulers for 'Eteint' mode"
  - "Schedulers for 'Chauffage' mode"
  - "Schedulers for 'Climatisation' mode"
  - "Schedulers for 'Ventilation' mode"
- Each field uses a multi-select entity selector for switch entities
- Users can select multiple scheduler switches for each mode

### 3. Translation Updates

**Files modified:**
- `custom_components/day_mode/strings.json`
- `custom_components/day_mode/translations/en.json`
- `custom_components/day_mode/translations/fr.json`

**Updates:**
- Removed thermostat_modes field labels
- Added scheduler configuration field labels for all 4 modes
- Updated descriptions to clarify that thermostat modes are fixed
- Both English and French translations updated

## Configuration Flow

### Initial Setup
When users first configure Day Mode, they will see:
- Calendar entity selection
- Optional holiday calendar
- Day modes (editable, comma-separated)
- Check time
- **No thermostat modes field** (automatically set to default values)

### Options Configuration
When users configure options, they will see all of the above plus:
- **Schedulers for Eteint mode** - Multi-select switch entities
- **Schedulers for Chauffage mode** - Multi-select switch entities
- **Schedulers for Climatisation mode** - Multi-select switch entities
- **Schedulers for Ventilation mode** - Multi-select switch entities

## Next Steps

To fully implement this feature, the following additional changes are needed:

1. **Update coordinator.py** to:
   - Read scheduler associations from `CONF_SCHEDULERS_PER_MODE`
   - Use these associations when refreshing schedulers
   - Handle scheduler state management based on current thermostat mode

2. **Update services** to:
   - Use scheduler associations when `refresh_schedulers` is called
   - Turn on appropriate schedulers based on current mode
   - Turn off schedulers for other modes

3. **Add documentation** explaining:
   - How to set up schedulers
   - How scheduler associations work
   - Examples of scheduler naming conventions

## Backward Compatibility

- Existing installations will continue to work
- The `thermostat_modes` field is kept in config data for backward compatibility
- Default thermostat modes will be used if not present in config
- Scheduler associations are optional and default to empty if not configured

## Testing

To test these changes:

1. Install or update the integration
2. Go to Settings → Devices & Services
3. Find Day Mode and click Configure
4. Verify that thermostat modes field is not shown
5. Verify that 4 scheduler selection fields are shown
6. Select scheduler switches for each mode
7. Save and verify configuration is stored correctly
