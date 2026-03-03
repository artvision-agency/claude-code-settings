#!/bin/bash
# Create Asana task from command line
# Usage: create-asana-task.sh "Task name" ["optional notes"]

TOKENS_FILE="$HOME/artvision-data/tokens.json"
TASK_NAME="$1"
NOTES="${2:-}"

if [ -z "$TASK_NAME" ]; then
    echo "Usage: create-asana-task.sh \"Task name\" [\"optional notes\"]"
    exit 1
fi

# Read Asana credentials from tokens.json
ASANA_TOKEN=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['asana']['token'])")
WORKSPACE_ID=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['asana']['workspace_id'])")

if [ -z "$ASANA_TOKEN" ] || [ -z "$WORKSPACE_ID" ]; then
    echo "Error: Could not read Asana credentials from $TOKENS_FILE"
    exit 1
fi

# Get first project in workspace (or use default)
PROJECT_ID=$(curl -s -X GET "https://app.asana.com/api/1.0/workspaces/${WORKSPACE_ID}/projects?limit=1" \
    -H "Authorization: Bearer ${ASANA_TOKEN}" \
    -H "Accept: application/json" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data['data'][0]['gid'] if data.get('data') else '')")

# Create task
RESPONSE=$(curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
    -H "Authorization: Bearer ${ASANA_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{
        \"data\": {
            \"workspace\": \"${WORKSPACE_ID}\",
            \"name\": \"${TASK_NAME}\",
            \"notes\": \"${NOTES}\n\n---\nCreated from Claude Code session\",
            \"projects\": [\"${PROJECT_ID}\"]
        }
    }")

TASK_GID=$(echo "$RESPONSE" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('data',{}).get('gid',''))")

if [ -n "$TASK_GID" ]; then
    echo "✅ Task created: https://app.asana.com/0/${PROJECT_ID}/${TASK_GID}"
else
    echo "❌ Error creating task:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
