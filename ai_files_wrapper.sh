#!/bin/bash

# AI Files Wrapper Script
# This script helps avoid permission issues with LaunchAgent

cd /Users/macbook/Developer/americo/ai-files

# Add full PATH to ensure all commands are found
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Use specific Python installation
/opt/homebrew/bin/python3 ai_files.py "$@"
