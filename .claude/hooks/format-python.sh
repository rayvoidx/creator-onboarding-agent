#!/bin/bash
# Post-edit hook: Format Python files with ruff
# Triggered after Edit/Write on *.py files

set -e

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

if [[ "$FILE_PATH" == *.py ]]; then
    # Check if ruff is available
    if command -v ruff &> /dev/null; then
        ruff format "$FILE_PATH" --quiet 2>/dev/null || true
        ruff check "$FILE_PATH" --fix --quiet 2>/dev/null || true
    fi
fi

exit 0
