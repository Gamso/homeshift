# Container Directory

This directory contains Docker-related files for running Day Mode in a containerized environment.

## Files

### docker-compose.yml

Docker Compose configuration for running Home Assistant with the Day Mode custom component.

**Usage:**
```bash
cd container
docker-compose up -d
```

This will:
- Start Home Assistant in a Docker container
- Mount the `config/` directory from the repository root
- Mount the `custom_components/day_mode` directory
- Expose Home Assistant on port 8123

**Access Home Assistant:**
- URL: http://localhost:8123
- Create an account on first run
- Navigate to Settings → Integrations → Add Integration → "Day Mode"

### starts_ha.sh

Startup script used by the development container to set up the environment.

This script:
- Creates necessary directories (`/config`, `/config/.storage`, `/config/custom_components`)
- Copies configuration from `.devcontainer/configuration.yaml` to `/config/`
- Copies scheduler storage from `.devcontainer/scheduler.storage` to `/config/.storage/`
- Creates a symlink for the day_mode custom component
- Sets proper permissions
- Starts Home Assistant

**Note:** This script is primarily used by the VS Code Dev Container setup (via `.devcontainer/devcontainer.json`). For Docker Compose usage, the volumes are mounted directly without needing this script.

## Directory Structure

```
container/
├── docker-compose.yml    # Docker Compose configuration
└── starts_ha.sh         # Dev container startup script
```

## Related Directories

- **`.devcontainer/`**: VS Code Dev Container configuration (uses `starts_ha.sh`)
- **`config/`**: Home Assistant configuration directory
- **`custom_components/day_mode/`**: The Day Mode integration code

## Development Workflow

### For Docker Compose Development:
```bash
cd container
docker-compose up -d
# Edit code in custom_components/day_mode/
# Restart Home Assistant to reload changes
docker-compose restart
```

### For VS Code Dev Container:
See [../.devcontainer/README.md](../.devcontainer/README.md)

The Dev Container approach is recommended as it provides:
- Pre-configured VS Code extensions
- Integrated debugging
- Automatic environment setup via `starts_ha.sh`
