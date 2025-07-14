#!/bin/bash

# finish_trading_system.sh
# This script helps complete the automated trading system using Claude Code

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Automated Trading System Completion Tool${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if claude is available
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: Claude Code CLI is not installed or not in PATH${NC}"
    echo -e "Please make sure Claude Code CLI is properly installed"
    exit 1
fi

# Define the project directory
PROJECT_DIR="$(pwd)"
echo -e "${YELLOW}Working in directory:${NC} $PROJECT_DIR"

# Define completion tasks
declare -a TASKS=(
    "Analyze the current state of the trading system and identify what components need to be completed for full automation"
    "Complete the balance_manager.py to track account balances and handle API rate limits properly"
    "Implement error handling and recovery mechanisms in the trading bot"
    "Create a proper startup script that initializes all necessary components"
    "Implement a proper shutdown procedure to safely close positions and save state"
    "Add comprehensive logging for all trading activities"
    "Implement a monitoring system to alert on issues"
    "Create a configuration system for easy parameter adjustment"
    "Add unit tests for critical components"
    "Implement a dashboard for real-time monitoring"
)

# Function to run Claude Code with a specific task
run_claude_task() {
    local task="$1"
    local task_file="claude_task_$(echo "$task" | head -c 20 | tr ' ' '_').txt"
    
    echo -e "${YELLOW}Task:${NC} $task"
    echo -e "${BLUE}Creating task file...${NC}"
    
    # Create the task file
    cat > "$task_file" << EOF
$task

Please analyze the existing code in this directory and provide:
1. A detailed assessment of what exists and what's missing
2. Code implementations for the missing components
3. Instructions on how to integrate the new code with the existing system
4. Tests to verify the implementation works correctly

Focus on making the trading system fully automated, robust, and error-resistant.
EOF
    
    echo -e "${GREEN}Running Claude Code with task...${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"
    
    # Run Claude Code with the task
    cat "$task_file" | claude
    
    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${GREEN}Task completed.${NC}"
    echo ""
}

# Main execution
echo -e "${YELLOW}Available tasks:${NC}"
for i in "${!TASKS[@]}"; do
    echo -e "${GREEN}$((i+1)).${NC} ${TASKS[$i]}"
done

echo ""
echo -e "${YELLOW}How do you want to proceed?${NC}"
echo -e "1. Run all tasks sequentially"
echo -e "2. Select a specific task"
echo -e "3. Enter a custom task"
echo -e "4. Exit"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}Running all tasks sequentially...${NC}"
        for task in "${TASKS[@]}"; do
            run_claude_task "$task"
            echo -e "${YELLOW}Waiting 5 seconds before next task...${NC}"
            sleep 5
        done
        ;;
    2)
        read -p "Enter task number (1-${#TASKS[@]}): " task_num
        if [[ $task_num -ge 1 && $task_num -le ${#TASKS[@]} ]]; then
            run_claude_task "${TASKS[$((task_num-1))]}"
        else
            echo -e "${RED}Invalid task number${NC}"
            exit 1
        fi
        ;;
    3)
        echo -e "${YELLOW}Enter your custom task:${NC}"
        read -e custom_task
        run_claude_task "$custom_task"
        ;;
    4)
        echo -e "${BLUE}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}All tasks completed. Your trading system should now be closer to completion.${NC}"
echo -e "${YELLOW}Don't forget to test thoroughly before deploying to production!${NC}" 