#!/bin/bash
# Balance Manager V2 Fixes Test Runner
# ===================================

echo "Starting Balance Manager V2 Fixes Test..."
echo

cd "/mnt/c/dev/tools/crypto-trading-bot-2025"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python not found in PATH"
        echo "Please ensure Python is installed and accessible"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version

# Run the test with proper error handling
echo "Running test script..."
$PYTHON_CMD test_balance_manager_fixes.py

TEST_EXIT_CODE=$?

echo
echo "Test completed with exit code: $TEST_EXIT_CODE"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "SUCCESS: All tests passed - Balance Manager V2 fixes are working!"
elif [ $TEST_EXIT_CODE -eq 2 ]; then
    echo "CRITICAL: NONCE AUTHENTICATION ISSUES DETECTED - Requires immediate attention"
else
    echo "WARNING: Some tests failed or were inconclusive"
fi

echo
echo "Check balance_manager_test.log for detailed output"
echo "Test results saved to balance_manager_test_results_*.json"

# Don't pause in WSL/Linux environment - just display final message
echo "Test runner completed."