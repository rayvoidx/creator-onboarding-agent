#!/bin/bash
# Pre-edit hook: Validate JSON files
# Blocks edit if JSON is invalid

set -e

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"
CONTENT="${CLAUDE_TOOL_INPUT:-}"

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

if [[ "$FILE_PATH" == *.json ]]; then
    # Validate JSON syntax
    if command -v python3 &> /dev/null; then
        echo "$CONTENT" | python3 -m json.tool > /dev/null 2>&1
        if [[ $? -ne 0 ]]; then
            echo "Invalid JSON syntax"
            exit 2  # Block the edit
        fi
    fi
fi

exit 0
