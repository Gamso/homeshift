#!/bin/bash
# Validation script for HomeShift custom component

set -e

echo "🔍 Validating HomeShift custom component..."

# Check if custom_components directory exists
if [ ! -d "custom_components/homeshift" ]; then
    echo "❌ Error: custom_components/homeshift directory not found"
    exit 1
fi

echo "✅ Directory structure OK"

# Validate Python syntax
echo "🐍 Checking Python syntax..."
python_files=$(find custom_components/homeshift -name "*.py")
for file in $python_files; do
    if python -m py_compile "$file"; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file"
        exit 1
    fi
done

# Validate JSON files
echo "📋 Checking JSON files..."
json_files=$(find custom_components/homeshift -name "*.json")
for file in $json_files; do
    if python -m json.tool "$file" > /dev/null; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file"
        exit 1
    fi
done

# Check required files
echo "📁 Checking required files..."
required_files=(
    "custom_components/homeshift/__init__.py"
    "custom_components/homeshift/manifest.json"
    "custom_components/homeshift/config_flow.py"
    "custom_components/homeshift/const.py"
    "README.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

echo ""
echo "✅ All validations passed!"
echo "🚀 Component is ready for testing"
