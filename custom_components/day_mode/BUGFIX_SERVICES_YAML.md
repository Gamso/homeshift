# Bug Fix: Services.yaml Schema Validation Error

## Issue

The Day Mode integration was failing to load with a schema validation error:

```
File "/home/vscode/.local/lib/python3.13/site-packages/homeassistant/helpers/service.py", line 498, in _load_services_file
    _SERVICES_SCHEMA(
        load_yaml_dict(str(integration.file_path / "services.yaml"))
    )
voluptuous.schema_builder.py:779 in validate_callable
```

## Root Cause

The `services.yaml` file was missing the required `fields` key for each service definition.

**Incorrect (before):**
```yaml
refresh_schedulers:
  name: Refresh Schedulers
  description: Refresh scheduler states...
  # Missing 'fields' key ❌
```

According to Home Assistant's service schema, **every service definition must have a `fields` key**, even if the service takes no parameters.

## Fix

Added `fields: {}` to both service definitions:

**Correct (after):**
```yaml
refresh_schedulers:
  name: Refresh Schedulers
  description: Refresh scheduler states based on current day mode and thermostat mode
  fields: {}  # ✅ Required - empty dict for services with no parameters

check_next_day:
  name: Check Next Day
  description: Check and update the day mode for the next day
  fields: {}  # ✅ Required - empty dict for services with no parameters
```

## Home Assistant Services Schema Requirements

According to Home Assistant documentation and schema validation, a service definition must have:

1. **name** (string) - Display name for the service
2. **description** (string) - Description of what the service does
3. **fields** (dict) - Parameters the service accepts
   - Can be empty `{}` if the service takes no parameters
   - Each field can have: name, description, required, selector, etc.

## Example with Parameters

If we later add parameters to our services, the format would be:

```yaml
refresh_schedulers:
  name: Refresh Schedulers
  description: Refresh scheduler states
  fields:
    force:
      name: Force Refresh
      description: Force refresh even if recently updated
      required: false
      selector:
        boolean:
```

## Testing

Validated with Python:
```python
import yaml
with open('services.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Verify structure
for service_name, service_data in data.items():
    assert 'name' in service_data
    assert 'description' in service_data
    assert 'fields' in service_data
    assert isinstance(service_data['fields'], dict)
```

## Status

✅ **FIXED** - Services now load successfully in Home Assistant

## Related Files

- `custom_components/day_mode/services.yaml` - Fixed
- `custom_components/day_mode/__init__.py` - Service registration (no changes needed)

## Lesson Learned

Always include the `fields` key in services.yaml, even when services take no parameters. Use an empty dict `{}` to indicate no parameters are required.
