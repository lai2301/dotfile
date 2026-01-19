#!/usr/bin/env bash

JSON=$(amdgpu_top -J -n 1 2>/dev/null) || {
  echo '{"text":"GPU N/A","tooltip":"amdgpu_top failed"}'
  exit 0
}

[[ -z "$JSON" ]] && {
  echo '{"text":"GPU N/A","tooltip":"No AMD GPU data"}'
  exit 0
}

# ── Main stats ──
GFX_PCT=$(jq -r '.devices[]."Total fdinfo".GFX.value // 0' <<<"$JSON" 2>/dev/null || echo "0")
VRAM_USED=$(jq -r '.devices[]."Total fdinfo".VRAM.value // 0' <<<"$JSON" 2>/dev/null || echo "0")
VRAM_TOTAL=$(jq -r '.devices[].VRAM."Total VRAM".value // 0' <<<"$JSON" 2>/dev/null || echo "0")

VRAM_USED_GIB=$(awk "BEGIN {printf \"%.1f\", $VRAM_USED/1024}" 2>/dev/null || echo "0")
VRAM_TOTAL_GIB=$(awk "BEGIN {printf \"%.1f\", $VRAM_TOTAL/1024}" 2>/dev/null || echo "0")
TEXT="GPU:${GFX_PCT}% VRAM:${VRAM_USED_GIB}G/${VRAM_TOTAL_GIB}G"

# ── Build tooltip array (we'll join with jq) ──
TOOLTIP_LINES=()
TOOLTIP_LINES+=("GPU Usage: ${GFX_PCT}%")
TOOLTIP_LINES+=("VRAM: ${VRAM_USED_GIB}G / ${VRAM_TOTAL_GIB}G")
TOOLTIP_LINES+=("")
TOOLTIP_LINES+=("--- Processes by VRAM ---")

# Extract process info and sort by VRAM usage (descending)
PROCESSES=$(jq -r '
  .devices[].fdinfo // {} | 
  to_entries | 
  map({
    name: .value.name,
    vram: (.value.usage.usage.VRAM.value // 0),
    gfx: (.value.usage.usage.GFX.value // 0)
  }) |
  sort_by(-.vram) |
  .[] |
  select(.vram > 0) |
  "\(.name)|\(.vram)|\(.gfx)"
' <<<"$JSON" 2>/dev/null || echo "")

# Format processes for tooltip
if [[ -n "$PROCESSES" ]]; then
  while IFS='|' read -r name vram gfx; do
    vram_mib=$(awk "BEGIN {printf \"%.0f\", $vram}" 2>/dev/null || echo "$vram")
    TOOLTIP_LINES+=("${name}: ${vram_mib}M (GFX:${gfx}%)")
  done <<<"$PROCESSES"
else
  TOOLTIP_LINES+=("No active processes")
fi

# Build final tooltip string with actual newlines
TOOLTIP=$(printf '%s\n' "${TOOLTIP_LINES[@]}")

# Use jq to properly encode the JSON (handles all escaping correctly)
# Output as compact JSON (single line) to avoid any parsing issues
jq -n -c --arg text "$TEXT" --arg tooltip "$TOOLTIP" '{text: $text, tooltip: $tooltip}'
