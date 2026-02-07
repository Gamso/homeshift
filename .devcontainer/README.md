# Day Mode Development Container

This directory contains configuration for developing the Day Mode custom component using Visual Studio Code Dev Containers or GitHub Codespaces.

## Prerequisites

- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (for local development)

## Quick Start

### Using VS Code Dev Containers (Local)

1. Open this repository in VS Code
2. Press `F1` or `Ctrl+Shift+P` (Cmd+Shift+P on Mac)
3. Select "Dev Containers: Reopen in Container"
4. Wait for the container to build and start
5. The container will automatically:
   - Install Home Assistant dev environment
   - Set up the custom component
   - Start Home Assistant on port 8123

### Using GitHub Codespaces (Cloud)

1. Navigate to the repository on GitHub
2. Click the green "Code" button
3. Select "Codespaces" tab
4. Click "Create codespace on main" (or your branch)
5. Wait for the codespace to initialize

## What's Included

The devcontainer includes:

- **Home Assistant Core**: Full development environment
- **Python Extensions**: Python, Pylance for IntelliSense
- **Linting & Formatting**: Ruff for code quality
- **YAML Support**: For Home Assistant configuration files
- **VS Code Settings**: Pre-configured for Home Assistant development

## Accessing Home Assistant

Once the container is running:

1. Open your browser to http://localhost:8123
2. Complete the initial Home Assistant setup
3. Navigate to Settings → Integrations
4. Click "Add Integration" and search for "Day Mode"

## Development Workflow

### Making Changes

1. Edit files in the `custom_components/day_mode` directory
2. Changes are automatically reflected in the running container
3. Restart Home Assistant to reload the integration:
   - Go to Developer Tools → YAML → Restart

### Debugging

1. Check logs in VS Code terminal: `ha logs`
2. Or view in Home Assistant UI: Settings → System → Logs
3. The devcontainer is configured with debug logging for `day_mode`

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-homeassistant-custom-component

# Run tests
pytest tests/
```

## Container Commands

The devcontainer includes the Home Assistant CLI (`ha`):

```bash
# Check Home Assistant status
ha core check

# View logs
ha core logs

# Restart Home Assistant
ha core restart

# Update Home Assistant
ha core update
```

## Troubleshooting

### Container won't start

- Ensure Docker Desktop is running
- Check Docker has enough resources (at least 4GB RAM recommended)
- Try rebuilding: "Dev Containers: Rebuild Container"

### Port 8123 already in use

- Stop any other Home Assistant instances
- Or change the port in `devcontainer.json` (e.g., `"9123:8123"`)

### Changes not reflected

- Restart Home Assistant: Developer Tools → YAML → Restart
- Or rebuild the container if changing dependencies

## Additional Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Day Mode Documentation](../README.md)
