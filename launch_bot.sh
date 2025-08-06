#!/bin/bash
# ============================================================================
# UNIFIED CRYPTO TRADING BOT LAUNCHER - LINUX/WSL
# Cross-platform launcher for all bot modes
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}    CRYPTO TRADING BOT - UNIFIED LAUNCHER${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to project directory
cd "$PROJECT_ROOT"

# Check Python installation
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python not found in PATH"
        print_error "Please install Python 3.8 or higher"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "Python found: $PYTHON_VERSION"

# Check if main.py exists
if [[ ! -f "main.py" ]]; then
    print_error "main.py not found in current directory"
    print_error "Current directory: $(pwd)"
    print_error "Expected location: $PROJECT_ROOT/main.py"
    exit 1
fi

print_success "Unified launcher found: main.py"

# Function to show usage
show_usage() {
    echo ""
    echo -e "${PURPLE}Usage:${NC}"
    echo "  $0 [MODE] [OPTIONS]"
    echo ""
    echo -e "${PURPLE}Available Modes:${NC}"
    echo "  --simple           Launch simple bot mode"
    echo "  --orchestrated     Launch orchestrated mode with full monitoring"
    echo "  --paper            Launch paper trading mode (safe simulation)"
    echo "  --test             Run component tests only"
    echo "  --status           Check current bot status"
    echo "  --info             Show environment information"
    echo "  --interactive      Interactive mode selection (default)"
    echo ""
    echo -e "${PURPLE}Options:${NC}"
    echo "  --config FILE      Use specific configuration file"
    echo "  --verbose          Enable verbose logging"
    echo "  --dry-run          Validate configuration without launching"
    echo "  --help             Show this help message"
    echo ""
    echo -e "${PURPLE}Examples:${NC}"
    echo "  $0                 # Interactive mode selection"
    echo "  $0 --simple        # Launch simple bot"
    echo "  $0 --paper         # Launch paper trading"
    echo "  $0 --test          # Run tests"
    echo "  $0 --status        # Check status"
    echo ""
}

# Parse command line arguments
MODE=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --simple|--orchestrated|--paper|--test|--status|--info)
            MODE="$1"
            shift
            ;;
        --interactive)
            MODE=""
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        --config|--verbose|--dry-run)
            EXTRA_ARGS+=("$1")
            if [[ "$1" == "--config" && $# -gt 1 ]]; then
                EXTRA_ARGS+=("$2")
                shift
            fi
            shift
            ;;
        *)
            print_warning "Unknown option: $1"
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

# Check environment and available modes
print_info "Checking environment and available modes..."
ENV_CHECK_OUTPUT=$($PYTHON_CMD main.py --info 2>/dev/null || echo "Environment check failed")

if [[ "$ENV_CHECK_OUTPUT" == *"Environment check failed"* ]]; then
    print_warning "Could not verify environment automatically"
    print_info "Proceeding with launch attempt..."
else
    print_success "Environment check completed"
fi

# Function to launch with specific mode
launch_bot() {
    local launch_mode="$1"
    local args=("${@:2}")
    
    print_info "Launching bot in $launch_mode mode..."
    print_info "Press Ctrl+C to interrupt at any time"
    echo ""
    
    # Set up signal handling for graceful shutdown
    trap 'print_warning "Received interrupt signal - shutting down..."; exit 130' INT TERM
    
    # Launch the bot
    if [[ "$launch_mode" == "interactive" ]]; then
        exec $PYTHON_CMD main.py "${args[@]}"
    else
        exec $PYTHON_CMD main.py "$launch_mode" "${args[@]}"
    fi
}

# Handle the selected mode
case "$MODE" in
    --simple)
        print_info "Selected: Simple Mode"
        print_info "Features: Core trading engine, basic monitoring"
        launch_bot "--simple" "${EXTRA_ARGS[@]}"
        ;;
    --orchestrated)
        print_info "Selected: Orchestrated Mode"
        print_info "Features: Full monitoring, diagnostics, WebSocket-first"
        launch_bot "--orchestrated" "${EXTRA_ARGS[@]}"
        ;;
    --paper)
        print_info "Selected: Paper Trading Mode"
        print_info "Features: Safe simulation, no real money at risk"
        launch_bot "--paper" "${EXTRA_ARGS[@]}"
        ;;
    --test)
        print_info "Selected: Component Tests"
        print_info "Running component validation tests..."
        launch_bot "--test" "${EXTRA_ARGS[@]}"
        ;;
    --status)
        print_info "Selected: Status Check"
        print_info "Checking current bot status..."
        launch_bot "--status" "${EXTRA_ARGS[@]}"
        ;;
    --info)
        print_info "Selected: Environment Information"
        launch_bot "--info" "${EXTRA_ARGS[@]}"
        ;;
    "")
        print_info "Selected: Interactive Mode"
        print_info "Starting interactive mode selection..."
        launch_bot "interactive" "${EXTRA_ARGS[@]}"
        ;;
    *)
        print_error "Invalid mode: $MODE"
        show_usage
        exit 1
        ;;
esac