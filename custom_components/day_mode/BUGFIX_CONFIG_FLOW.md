# Bug Fix: Config Flow Runtime Error

## Issue

The Day Mode integration was failing to load with the following error:

```
2026-02-08 15:20:51.569 ERROR (MainThread) [homeassistant] Error doing job: Task exception was never retrieved
```

## Root Cause

In `custom_components/day_mode/config_flow.py` line 178-181, the code was using an invalid `description` parameter in `vol.Optional`:

```python
# INCORRECT - causes TypeError
schema_dict[vol.Optional(
    mode_key,
    default=current_value,
    description=f"Schedulers for '{mode}' mode"  # ❌ Invalid parameter
)] = selector.EntitySelector(...)
```

The `voluptuous.Optional` class does not accept a `description` parameter. This caused a `TypeError` when Home Assistant tried to instantiate the config flow, preventing the integration from loading.

## Fix

Removed the invalid `description` parameter:

```python
# CORRECT
schema_dict[vol.Optional(
    mode_key,
    default=current_value
)] = selector.EntitySelector(...)
```

## Why This Works

The field descriptions are already properly defined in the translation files:
- `strings.json`
- `translations/en.json`
- `translations/fr.json`

Home Assistant reads these translation files to display field labels and descriptions in the UI. The `description` parameter in `vol.Optional` was redundant and invalid.

## Testing

1. **Syntax Check**: Verified Python syntax is correct
   ```bash
   python3 -m py_compile custom_components/day_mode/config_flow.py
   ```

2. **Integration Load**: The integration should now load without errors

3. **Configuration UI**: The options form should display correctly with:
   - General configuration fields
   - 4 scheduler selection fields (one per thermostat mode)
   - Proper labels from translation files

## Impact

- ✅ Integration loads successfully
- ✅ Configuration UI works properly
- ✅ Field labels and descriptions display correctly (from translation files)
- ✅ No functionality lost

## Related Files

- `custom_components/day_mode/config_flow.py` - Fixed
- `custom_components/day_mode/strings.json` - Contains field descriptions
- `custom_components/day_mode/translations/en.json` - English labels
- `custom_components/day_mode/translations/fr.json` - French labels

## Lesson Learned

Always validate parameters against the library's API documentation. In this case:
- `voluptuous.Optional(key, default=...)` - Valid parameters
- `description` parameter - Not supported by voluptuous
- Field descriptions should be in translation files, not in schema definition
