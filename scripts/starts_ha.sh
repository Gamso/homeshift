#!/bin/bash
set -e
set -x

cd "$(dirname "$0")/.."
pwd

# Create config dir if not present
if [[ ! -d "${PWD}/config" ]]; then
    mkdir -p "${PWD}/config"
    # Add defaults configuration
    hass --config "${PWD}/config" --script ensure_config
fi

echo ""
echo "🔗 Setting up configuration files..."

# Overwrite configuration.yaml if provided
if [ -f ${PWD}/.devcontainer/configuration.yaml ]; then
    rm -f ${PWD}/config/configuration.yaml
    ln -s ${PWD}/.devcontainer/configuration.yaml ${PWD}/config/configuration.yaml
	echo "   ✅ Configuration linked"
fi

# Link ui-lovelace.yaml for dashboard
if [ -f ${PWD}/.devcontainer/ui-lovelace.yaml ]; then
    rm -f ${PWD}/config/ui-lovelace.yaml
    ln -s ${PWD}/.devcontainer/ui-lovelace.yaml ${PWD}/config/ui-lovelace.yaml
	echo "   ✅ Lovelace dashboard linked"
fi

# Copy scheduler.storage if it exists
if [ -f ${PWD}/.devcontainer/scheduler.storage ]; then
	# Only create .storage directory if it doesn't exist
	mkdir -p "${PWD}/config/.storage"
	# Remove old scheduler.storage symlink/file if it exists
	rm -f ${PWD}/config/.storage/scheduler.storage
	# Create new symlink
    ln -s ${PWD}/.devcontainer/scheduler.storage ${PWD}/config/.storage/scheduler.storage
	echo "   ✅ Scheduler storage linked"
fi

# Dev-only custom_components
if [ ! -d ${PWD}/config/custom_components ]; then
    mkdir -p ${PWD}/config/custom_components
fi


echo ""
echo "📦 Installing scheduler-component..."
SCHEDULER_COMPONENT_VERSION="v3.3.8"
SCHEDULER_COMPONENT_URL="https://github.com/nielsfaber/scheduler-component/releases/download/${SCHEDULER_COMPONENT_VERSION}/scheduler.zip"

if [ ! -d ${PWD}/config/custom_components/scheduler ]; then
    # Install wget and unzip if not available
    if ! command -v wget &> /dev/null || ! command -v unzip &> /dev/null; then
        echo "   Installing wget and unzip..."
        apk add --no-cache wget unzip > /dev/null 2>&1
    fi

    echo "   Downloading scheduler-component ${SCHEDULER_COMPONENT_VERSION}..."
    if wget -q ${SCHEDULER_COMPONENT_URL} -O /tmp/scheduler.zip; then
        echo "   Extracting scheduler component..."
        # Extract to temporary location to handle different ZIP structures
        SCHEDULER_TEMP="/tmp/scheduler_temp_$$"
        mkdir -p ${SCHEDULER_TEMP}
        unzip -q /tmp/scheduler.zip -d ${SCHEDULER_TEMP}
        rm /tmp/scheduler.zip

        # Check if scheduler folder already exists in extracted files
        if [ -d ${SCHEDULER_TEMP}/scheduler ]; then
            # ZIP already contained scheduler directory
            mv ${SCHEDULER_TEMP}/scheduler ${PWD}/config/custom_components/
        else
            # ZIP had files at root level, create scheduler folder and move files
            mkdir -p ${PWD}/config/custom_components/scheduler
            mv ${SCHEDULER_TEMP}/* ${PWD}/config/custom_components/scheduler/ 2>/dev/null || true
        fi
        rm -rf ${SCHEDULER_TEMP}

        # Verify installation
        if [ -f ${PWD}/config/custom_components/scheduler/manifest.json ]; then
            echo "   ✅ Scheduler component installed successfully!"
            echo "   📁 Location: ${PWD}/config/custom_components/scheduler/"
        else
            echo "   ⚠️  Warning: scheduler component extracted but manifest.json not found"
            echo "   Checking what was extracted..."
            ls -la ${PWD}/config/custom_components/ || true
        fi
    else
        echo "   ⚠️  Failed to download scheduler component"
    fi
else
    echo "   ✅ Scheduler component already installed"
    echo "   📁 Location: ${PWD}/config/custom_components/scheduler/"
    # Verify it's properly installed
    if [ -f ${PWD}/config/custom_components/scheduler/manifest.json ]; then
        echo "   ✓ manifest.json found"
    else
        echo "   ⚠️  Warning: manifest.json not found in scheduler directory"
    fi
fi

echo ""
echo "📦 Installing scheduler-card..."
SCHEDULER_CARD_VERSION="v4.0.11"
SCHEDULER_CARD_URL="https://github.com/nielsfaber/scheduler-card/releases/download/${SCHEDULER_CARD_VERSION}/scheduler-card.js"

# Create scheduler-card directory
mkdir -p ${PWD}/config/www/scheduler-card

if [ ! -f ${PWD}/config/www/scheduler-card/scheduler-card.js ]; then
    # Install wget if not available
    if ! command -v wget &> /dev/null; then
        echo "   Installing wget..."
        apk add --no-cache wget > /dev/null 2>&1
    fi

    echo "   Downloading scheduler-card ${SCHEDULER_CARD_VERSION}..."
    if wget -q ${SCHEDULER_CARD_URL} -O ${PWD}/config/www/scheduler-card/scheduler-card.js; then
        echo "   ✅ Scheduler card installed!"
    else
        echo "   ⚠️  Failed to download scheduler card"
    fi
else
    echo "   ✅ Scheduler card already installed"
fi

echo ""
echo "🚀 Starting Home Assistant in the background..."




# Set the path to custom_components
## This let's us have the structure we want <root>/custom_components/integration_blueprint
## while at the same time have Home Assistant configuration inside <root>/config
## without resulting to symlinks.
export PYTHONPATH="${PWD}:${PWD}/config:${PYTHONPATH}"

# Start Home Assistant
hass --config "${PWD}/config" --debug