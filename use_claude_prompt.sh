#!/bin/bash

# Bash script to run Claude Code with our trading bot fixes prompt
# This script helps you use Claude Code with the prepared prompt

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Claude Code Trading Bot Fix Assistant${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if claude is available
if ! command -v claude &> /dev/null; then
    echo -e "${RED}[ERROR] Claude Code CLI is not installed or not in PATH${NC}"
    echo -e "Please make sure Claude Code CLI is properly installed"
    exit 1
fi

# Define the project directory
PROJECT_DIR="$(pwd)"
echo -e "${YELLOW}[INFO] Project path: ${PROJECT_DIR}${NC}"

# Check if prompt files exist
PROMPT_FILES=(
    "claude_prompt_trading_bot_fixes.md:General Fixes Prompt"
    "claude_code_trading_rules_prompt.md:Trading Rules Prompt"
    "CLAUDE_CODE_RULES.md:Claude Code Rules"
)

for PROMPT_FILE_INFO in "${PROMPT_FILES[@]}"; do
    PROMPT_FILE="${PROMPT_FILE_INFO%%:*}"
    PROMPT_NAME="${PROMPT_FILE_INFO#*:}"
    
    if [ ! -f "$PROJECT_DIR/$PROMPT_FILE" ]; then
        echo -e "${RED}[ERROR] Prompt file not found at ${PROJECT_DIR}/${PROMPT_FILE}${NC}"
        exit 1
    fi
    echo -e "${GREEN}[INFO] Found prompt file: ${PROMPT_NAME}${NC}"
done

# Function to show menu
show_menu() {
    echo -e "\n${BLUE}[MENU] Choose an option:${NC}"
    echo -e "1. Run Claude Code with general trading bot fixes prompt"
    echo -e "2. Run Claude Code with trading rules implementation prompt"
    echo -e "3. Run Claude Code with both prompts (comprehensive fix)"
    echo -e "4. View Claude Code Rules for crypto trading"
    echo -e "5. Start Claude Code in interactive mode"
    echo -e "6. Run Claude Code with specific file analysis"
    echo -e "7. Exit"
    
    read -p "Enter your choice (1-7): " choice
    
    case $choice in
        1)
            echo -e "${GREEN}[ACTION] Running Claude Code with general trading bot fixes prompt...${NC}"
            cat "$PROJECT_DIR/claude_prompt_trading_bot_fixes.md" | claude
            ;;
        2)
            echo -e "${GREEN}[ACTION] Running Claude Code with trading rules implementation prompt...${NC}"
            cat "$PROJECT_DIR/claude_code_trading_rules_prompt.md" | claude
            ;;
        3)
            echo -e "${GREEN}[ACTION] Running Claude Code with comprehensive fix approach...${NC}"
            cat "$PROJECT_DIR/CLAUDE_CODE_RULES.md" "$PROJECT_DIR/claude_prompt_trading_bot_fixes.md" "$PROJECT_DIR/claude_code_trading_rules_prompt.md" | claude
            ;;
        4)
            echo -e "${GREEN}[ACTION] Viewing Claude Code Rules...${NC}"
            cat "$PROJECT_DIR/CLAUDE_CODE_RULES.md"
            echo -e "\nPress Enter to continue..."
            read
            ;;
        5)
            echo -e "${GREEN}[ACTION] Starting Claude Code in interactive mode...${NC}"
            claude
            ;;
        6)
            read -p "Enter path to file to analyze (relative to project root): " file_path
            if [ -z "$file_path" ]; then
                echo -e "${RED}[ERROR] File path cannot be empty${NC}"
            else
                echo -e "${GREEN}[ACTION] Running Claude Code to analyze ${file_path}...${NC}"
                echo "Analyze this file and suggest improvements to make it more robust and handle errors better according to the rules in CLAUDE_CODE_RULES.md: ${file_path}" | claude
            fi
            ;;
        7)
            echo -e "${YELLOW}[INFO] Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}[ERROR] Invalid choice. Please try again.${NC}"
            ;;
    esac
    
    # Return to menu after command completes
    show_menu
}

# Start the menu
show_menu 