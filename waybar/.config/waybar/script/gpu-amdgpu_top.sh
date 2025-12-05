#!/usr/bin/env bash

JSON=$(amdgpu_top -J -n 1 2>/dev/null)
[[ -z "$JSON" ]] && { echo '{"text":"GPU N/A","tooltip":"No AMD GPU"}'; exit 0; }

# ── Main stats ──
GFX_PCT=$(jq -r '.devices[]."Total fdinfo".GFX.value // 0' <<<"$JSON")
VRAM_USED=$(jq -r '.devices[]."Total fdinfo".VRAM.value // 0' <<<"$JSON")
VRAM_TOTAL=$(jq -r '.devices[].VRAM."Total VRAM".value // 0' <<<"$JSON")

VRAM_USED_GIB=$(awk "BEGIN {printf \"%.1f\", $VRAM_USED/1024}")
VRAM_TOTAL_GIB=$(awk "BEGIN {printf \"%.1f\", $VRAM_TOTAL/1024}")
TEXT="GPU:${GFX_PCT}% VRAM:${VRAM_USED_GIB}G/${VRAM_TOTAL_GIB}G"

echo "$TEXT"
