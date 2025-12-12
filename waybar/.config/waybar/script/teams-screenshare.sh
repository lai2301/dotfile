#!/bin/bash

# Check if video capture process is running
if ! pgrep -f "video_capture" >/dev/null; then
  echo '{"text": ""}'
  exit 0
fi

# Screen sharing is active, gather details
declare -a tooltip_lines=("Screen sharing active")

# Get PipeWire stream information (resolution and framerate)
if command -v pw-dump >/dev/null 2>&1; then
  stream_info=$(pw-dump 2>/dev/null | jq -r '
    .[] | select(
      .type == "PipeWire:Interface:Node" and 
      .info.props."media.class" == "Video/Source" and 
      .info.props."node.name" == "xdg-desktop-portal-hyprland"
    ) | .info.params.Format[0] // empty | 
    "\(.size.width)x\(.size.height)@\(.maxFramerate.num)fps"
  ' 2>/dev/null)
  
  if [ -n "$stream_info" ]; then
    tooltip_lines+=("Resolution: $stream_info")
  fi
fi

# Check which monitors are being affected (blocked from direct scanout)
if command -v hyprctl >/dev/null 2>&1; then
  blocked_monitors=$(hyprctl monitors -j 2>/dev/null | jq -r '
    .[] | select(.directScanoutBlockedBy | type == "array" and any(. == "RECORD")) | 
    "\(.name) (\(.width)x\(.height))"
  ' 2>/dev/null)
  
  if [ -n "$blocked_monitors" ]; then
    tooltip_lines+=("Monitors affected:")
    while IFS= read -r monitor; do
      tooltip_lines+=("  • $monitor")
    done <<< "$blocked_monitors"
  fi
fi

# Build tooltip with newlines
tooltip=$(printf '%s\\n' "${tooltip_lines[@]}" | sed '$s/\\n$//')

echo "{\"text\": \"󰻂\", \"tooltip\": \"$tooltip\", \"class\": \"active\"}"
