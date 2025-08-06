#!/bin/bash
# Cleanup unnecessary Node.js dependencies from Python project

echo "🧹 Cleaning up Node.js dependencies from crypto trading bot..."

# Remove node_modules
if [ -d "node_modules" ]; then
    echo "Removing node_modules directory..."
    rm -rf node_modules
fi

# Remove package-lock.json
if [ -f "package-lock.json" ]; then
    echo "Removing package-lock.json..."
    rm package-lock.json
fi

# Archive package.json for reference but remove it
if [ -f "package.json" ]; then
    echo "Archiving and removing package.json..."
    mv package.json package.json.archived
fi

# Clean npm cache
echo "Cleaning npm cache..."
npm cache clean --force 2>/dev/null || true

echo "✅ Node.js cleanup complete!"
echo "This is a Python project and doesn't need Node.js dependencies."