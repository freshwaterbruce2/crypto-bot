#!/bin/bash

echo "========================================="
echo "Installing MCP Configuration"
echo "========================================="
echo ""

CONFIG_DIR="/mnt/c/Users/fresh_zxae3v6/AppData/Roaming/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "Checking Claude configuration directory..."
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Creating directory: $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
fi

echo ""
echo "Choose configuration to install:"
echo "1. Full Access (single filesystem server with all directories)"
echo "2. Organized (separate filesystem servers for projects, data, user)"
echo ""
read -p "Enter your choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo "Installing Full Access configuration..."
    cp -f claude_desktop_full_access_config.json "$CONFIG_FILE"
elif [ "$choice" = "2" ]; then
    echo "Installing Organized configuration..."
    cp -f claude_desktop_organized_config.json "$CONFIG_FILE"
else
    echo "Invalid choice. Exiting."
    exit 1
fi

if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "========================================="
    echo "SUCCESS! Configuration installed."
    echo "========================================="
    echo ""
    echo "File access granted to:"
    echo "- C:\\projects050625 (all projects)"
    echo "- D:\\ (entire drive)"
    echo "- Desktop, Documents, Downloads"
    echo ""
    echo "Next steps:"
    echo "1. Close Claude Desktop completely"
    echo "2. Restart Claude Desktop"
    echo "3. Your MCP servers will start automatically"
    echo ""
else
    echo "ERROR: Failed to copy configuration file"
fi