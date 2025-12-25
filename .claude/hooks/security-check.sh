#!/bin/bash
# Pre-tool hook: Security check for sensitive operations
# Blocks potentially dangerous commands

set -e

TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
COMMAND="${CLAUDE_TOOL_INPUT:-}"

# Block dangerous patterns
DANGEROUS_PATTERNS=(
    "rm -rf /"
    "rm -rf ~"
    ":(){ :|:& };:"
    "> /dev/sda"
    "mkfs"
    "dd if="
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if [[ "$COMMAND" == *"$pattern"* ]]; then
        echo "Blocked: Dangerous command pattern detected"
        exit 2  # Block the operation
    fi
done

# Block access to sensitive files
SENSITIVE_FILES=(
    ".env"
    "credentials"
    "secrets"
    "private_key"
    "id_rsa"
)

for sensitive in "${SENSITIVE_FILES[@]}"; do
    if [[ "$COMMAND" == *"$sensitive"* ]] && [[ "$TOOL_NAME" == "Read" ]]; then
        echo "Blocked: Access to sensitive file"
        exit 2
    fi
done

exit 0
