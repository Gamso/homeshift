#!/bin/bash
# Validation script for Day Mode custom component

set -e

echo "🔍 Validating Day Mode custom component..."

# Check if custom_components directory exists
if [ ! -d "custom_components/day_mode" ]; then
    echo "❌ Error: custom_components/day_mode directory not found"
    exit 1
fi

echo "✅ Directory structure OK"

# Validate Python syntax
echo "🐍 Checking Python syntax..."
python_files=$(find custom_components/day_mode -name "*.py")
for file in $python_files; do
    python -m py_compile "$file"
    if [ $? -eq 0 ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file"
        exit 1
    fi
done

# Validate JSON files
echo "📋 Checking JSON files..."
json_files=$(find custom_components/day_mode -name "*.json")
for file in $json_files; do
    python -m json.tool "$file" > /dev/null
    if [ $? -eq 0 ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file"
        exit 1
    fi
done

# Check required files
echo "📁 Checking required files..."
required_files=(
    "custom_components/day_mode/__init__.py"
    "custom_components/day_mode/manifest.json"
    "custom_components/day_mode/config_flow.py"
    "custom_components/day_mode/const.py"
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
