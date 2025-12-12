#!/bin/bash

# Cache file location (same as external-ip.sh)
CACHE_FILE="/tmp/waybar-external-ip-cache"

# Extract IP from cache or fetch it fresh
if [ -f "$CACHE_FILE" ]; then
  # Extract IP from the JSON in cache
  external_ip=$(jq -r '.tooltip' "$CACHE_FILE" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
else
  # Fetch fresh if cache doesn't exist
  external_ip=$(curl -s --max-time 3 "ifconfig.me" 2>/dev/null)
fi

if [ -n "$external_ip" ]; then
  # Copy to clipboard using wl-copy (Wayland)
  if command -v wl-copy >/dev/null 2>&1; then
    echo -n "$external_ip" | wl-copy
    
    # Send notification if notify-send is available
    if command -v notify-send >/dev/null 2>&1; then
      notify-send -t 2000 "External IP Copied" "$external_ip copied to clipboard"
    fi
  # Fallback to xclip for X11
  elif command -v xclip >/dev/null 2>&1; then
    echo -n "$external_ip" | xclip -selection clipboard
    if command -v notify-send >/dev/null 2>&1; then
      notify-send -t 2000 "External IP Copied" "$external_ip copied to clipboard"
    fi
  else
    if command -v notify-send >/dev/null 2>&1; then
      notify-send -t 3000 "Error" "No clipboard tool found (wl-copy or xclip)"
    fi
  fi
else
  if command -v notify-send >/dev/null 2>&1; then
    notify-send -t 2000 "Error" "Could not retrieve external IP"
  fi
fi

