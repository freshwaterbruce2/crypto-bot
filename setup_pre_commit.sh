#!/bin/bash
# Setup pre-commit hooks for the crypto trading bot

echo "🚀 Setting up pre-commit hooks for crypto trading bot..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Install pre-commit if not already installed
echo "📦 Installing pre-commit..."
pip install pre-commit

# Install the git hooks
echo "🔗 Installing git hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Create secrets baseline
echo "🔐 Creating secrets baseline..."
detect-secrets scan > .secrets.baseline 2>/dev/null || true

# Run pre-commit on all files for initial cleanup
echo "🧹 Running initial code cleanup..."
pre-commit run --all-files || true

echo "✅ Pre-commit setup complete!"
echo ""
echo "Pre-commit will now automatically:"
echo "  • Format Python code with Black"
echo "  • Sort imports with isort"
echo "  • Lint with ruff"
echo "  • Check for security issues"
echo "  • Scan for hardcoded secrets"
echo "  • Validate commit messages"
echo ""
echo "To manually run all checks: pre-commit run --all-files"