#!/bin/bash
# Update Agent Status Script
# Usage: ./update_agent_status.sh <AGENT_ID> <STATUS> [TASK_DESCRIPTION]
#
# AGENT_ID: HUNTER, ORCHESTRATOR, BUILDER, INSPECTOR, LEDGER, GATEKEEPER
# STATUS: idle, working, blocked_internal, blocked_user
# TASK_DESCRIPTION: Optional description of current task

API_URL="${NEXUS_API_URL:-http://localhost:8000}"
AGENT_ID="$1"
STATUS="$2"
TASK="$3"

if [ -z "$AGENT_ID" ] || [ -z "$STATUS" ]; then
    echo "Usage: $0 <AGENT_ID> <STATUS> [TASK_DESCRIPTION]"
    echo ""
    echo "AGENT_ID: HUNTER, ORCHESTRATOR, BUILDER, INSPECTOR, LEDGER, GATEKEEPER"
    echo "STATUS: idle, working, blocked_internal, blocked_user"
    exit 1
fi

# Build JSON payload
if [ -z "$TASK" ]; then
    PAYLOAD="{\"status\": \"$STATUS\"}"
else
    PAYLOAD="{\"status\": \"$STATUS\", \"current_task\": \"$TASK\"}"
fi

# Call API
curl -s -X PUT "$API_URL/api/v1/agents/$AGENT_ID/status" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD"

echo ""
