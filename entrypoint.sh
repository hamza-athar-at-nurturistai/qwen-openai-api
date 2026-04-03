#!/bin/bash
set -e

# Write Qwen OAuth credentials if provided
if [ -n "$QWEN_ACCESS_TOKEN" ]; then
  mkdir -p /root/.qwen
  cat > /root/.qwen/oauth_creds.json << JSONEOF
{
  "access_token": "${QWEN_ACCESS_TOKEN}",
  "token_type": "Bearer",
  "refresh_token": "${QWEN_REFRESH_TOKEN}",
  "resource_url": "portal.qwen.ai",
  "expiry_date": 1893456000000
}
JSONEOF
  echo "Qwen OAuth credentials configured"
fi

# Execute the main command
exec "$@"
