#!/bin/bash
set -e

echo "Starting Home Assistant setup for Day Mode development..."

# Define paths
WORKSPACE_DIR="/workspaces/day_mode"
CONFIG_DIR="/config"
STORAGE_DIR="${CONFIG_DIR}/.storage"
CUSTOM_COMPONENTS_DIR="${CONFIG_DIR}/custom_components"
DEVCONTAINER_DIR="${WORKSPACE_DIR}/.devcontainer"

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p "${STORAGE_DIR}"
mkdir -p "${CUSTOM_COMPONENTS_DIR}"

# Copy devcontainer configuration to config directory
echo "Copying devcontainer configuration..."
if [ -f "${DEVCONTAINER_DIR}/configuration.yaml" ]; then
    cp "${DEVCONTAINER_DIR}/configuration.yaml" "${CONFIG_DIR}/configuration.yaml"
    echo "✓ Configuration copied"
fi

# Copy scheduler.storage if it exists
if [ -f "${DEVCONTAINER_DIR}/scheduler.storage" ]; then
    echo "Copying scheduler.storage to .storage directory..."
    cp "${DEVCONTAINER_DIR}/scheduler.storage" "${STORAGE_DIR}/scheduler.storage"
    echo "✓ Scheduler storage copied"
else
    echo "⚠ No scheduler.storage found in .devcontainer directory"
fi

# Create symlink for custom component
echo "Setting up day_mode custom component..."
if [ -d "${WORKSPACE_DIR}/custom_components/day_mode" ]; then
    # Remove existing symlink or directory if it exists
    rm -rf "${CUSTOM_COMPONENTS_DIR}/day_mode"
    
    # Create symlink
    ln -sf "${WORKSPACE_DIR}/custom_components/day_mode" "${CUSTOM_COMPONENTS_DIR}/day_mode"
    echo "✓ Symlink created: ${CUSTOM_COMPONENTS_DIR}/day_mode -> ${WORKSPACE_DIR}/custom_components/day_mode"
else
    echo "⚠ day_mode custom component not found at ${WORKSPACE_DIR}/custom_components/day_mode"
fi

# Set proper permissions
echo "Setting permissions..."
chmod -R 755 "${CONFIG_DIR}"
chown -R root:root "${CONFIG_DIR}"

echo ""
echo "✅ Setup complete!"
echo "Home Assistant configuration directory: ${CONFIG_DIR}"
echo "Custom components: ${CUSTOM_COMPONENTS_DIR}"
echo ""
echo "Starting Home Assistant..."

# Start Home Assistant
exec hass -c "${CONFIG_DIR}"
