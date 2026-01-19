#!/bin/bash

# Cache file to avoid too many API calls
CACHE_FILE="/tmp/waybar-external-ip-cache"
CACHE_DURATION=300  # 5 minutes

# Check if cache exists and is fresh
if [ -f "$CACHE_FILE" ]; then
  cache_age=$(($(date +%s) - $(stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)))
  if [ $cache_age -lt $CACHE_DURATION ]; then
    cat "$CACHE_FILE"
    exit 0
  fi
fi

# Fetch external IP (try multiple services for reliability)
external_ip=""
for service in "ifconfig.me" "icanhazip.com" "ipinfo.io/ip"; do
  external_ip=$(curl -s --max-time 3 "$service" 2>/dev/null | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
  if [ -n "$external_ip" ]; then
    break
  fi
done

if [ -n "$external_ip" ]; then
  # Get location info (optional)
  location=$(curl -s --max-time 3 "ipinfo.io/$external_ip/json" 2>/dev/null | jq -r '"\(.city // "Unknown"), \(.country // "")"' 2>/dev/null)
  
  if [ -n "$location" ] && [ "$location" != "null, null" ]; then
    output="{\"text\": \"󰩟\", \"tooltip\": \"External IP: $external_ip\\n$location\", \"class\": \"connected\"}"
  else
    output="{\"text\": \"󰩟\", \"tooltip\": \"External IP: $external_ip\", \"class\": \"connected\"}"
  fi
  
  echo "$output" > "$CACHE_FILE"
  echo "$output"
else
  echo '{"text": "󰩟", "tooltip": "External IP: unavailable", "class": "disconnected"}'
fi

