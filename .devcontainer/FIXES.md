# Fixes for Home Assistant Development Environment

## Issues Fixed

### 1. Dashboard ui-lovelace.yaml not displaying

**Problem:** The dashboard defined in `ui-lovelace.yaml` was not being displayed in Home Assistant.

**Root Cause:** The configuration file had `lovelace: mode: storage`, which tells Home Assistant to use the UI editor and ignore the `ui-lovelace.yaml` file.

**Solution:** Changed the lovelace mode to `yaml` in `.devcontainer/configuration.yaml`:
```yaml
lovelace:
  mode: yaml  # Changed from 'storage' to 'yaml'
```

This allows Home Assistant to load the dashboard from `ui-lovelace.yaml` instead of using the storage-based UI editor.

### 2. Scheduler-card not available

**Problem:** The scheduler-card was not showing up in the Lovelace interface.

**Root Causes:**
1. Wrong resource URL in configuration (pointed to `/local/day_mode_card/day-mode-card.js`)
2. Scheduler integration not declared in configuration

**Solutions:**
1. Fixed the resource URL to point to the correct location:
```yaml
resources:
  - url: /local/scheduler-card/scheduler-card.js
    type: module
```

2. Added scheduler integration configuration:
```yaml
scheduler:
  # No specific config needed, component will auto-configure
```

The `starts_ha.sh` script already downloads and installs:
- The scheduler component (custom integration) to `config/custom_components/scheduler/`
- The scheduler-card (Lovelace card) to `config/www/scheduler-card/scheduler-card.js`

### 3. Losing all configuration on restart

**Problem:** When restarting Home Assistant (via "Restart Home Assistant on port 8123" task), all configuration was lost and the setup wizard appeared again.

**Root Cause:** The `starts_ha.sh` script was deleting the entire `.storage` directory with `rm -rf ${PWD}/config/.storage`, which contains:
- `core.config_entries` - Integration configurations
- `core.entity_registry` - Entity registry
- `core.device_registry` - Device registry  
- `lovelace.*` - Lovelace UI configurations
- And many other important files

**Solution:** Modified the script to only remove/update the specific `scheduler.storage` file instead of deleting the entire directory:

```bash
# Before (BAD):
rm -rf ${PWD}/config/.storage  # Deletes EVERYTHING!
mkdir -p "${PWD}/config/.storage"
ln -s ${PWD}/.devcontainer/scheduler.storage ${PWD}/config/.storage/scheduler.storage

# After (GOOD):
mkdir -p "${PWD}/config/.storage"  # Create only if doesn't exist
rm -f ${PWD}/config/.storage/scheduler.storage  # Remove only scheduler.storage
ln -s ${PWD}/.devcontainer/scheduler.storage ${PWD}/config/.storage/scheduler.storage
```

This preserves all other storage files, maintaining:
- User accounts and authentication
- Integration configurations (including Day Mode)
- Entity customizations
- All other Home Assistant state

## How It Works Now

1. **First startup:**
   - `starts_ha.sh` creates config directory
   - Links configuration.yaml and ui-lovelace.yaml
   - Creates .storage directory if needed
   - Links scheduler.storage
   - Downloads scheduler component and card
   - Starts Home Assistant

2. **Subsequent restarts:**
   - Existing .storage files are preserved
   - Only scheduler.storage link is refreshed
   - All user configuration, integrations, and state remain intact
   - No need to go through setup wizard again

## Testing

To verify the fixes work:

1. **Start Home Assistant:**
   - Open project in VS Code Dev Container
   - Container will auto-start with `./container dev-setup`
   - Then run "Start Home Assistant on port 8123" task

2. **Verify dashboard:**
   - Access http://localhost:8123
   - Complete initial setup if first time
   - Navigate to the dashboard
   - You should see the "Scheduler" view defined in ui-lovelace.yaml

3. **Verify scheduler-card:**
   - Go to Settings → Devices & Services
   - Click "Add Integration" 
   - Search for "Scheduler" and add it
   - Go to the "Scheduler" dashboard view
   - The scheduler-card should display

4. **Verify persistence:**
   - Make some changes (add an integration, customize entities, etc.)
   - Run "Restart Home Assistant on port 8123" task
   - After restart, all your changes should still be there
   - You should NOT see the setup wizard again

## Files Modified

1. `.devcontainer/configuration.yaml` - Fixed lovelace mode and resources
2. `scripts/starts_ha.sh` - Fixed .storage directory handling
