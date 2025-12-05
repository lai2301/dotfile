#!/bin/bash
# ------------------------------------------------------------
# File:   filetoggler.sh
# Purpose: Browse directories with fzf and run `fileup` on the
#          chosen folder(s).  Supports "Alt‑O" (go up) and
#          "Alt‑I" (open one level deeper).
# ------------------------------------------------------------

set -euo pipefail   # safer Bash defaults

BASE_PATH="/home/lai2301"

# Default path: ~/Downloads.  If the user selects nothing, we fall back to this.
DEFAULT_DIR="${HOME}/Downloads"

# Temporary file to track current directory during navigation
STATE_FILE=$(mktemp)
echo "$HOME" > "$STATE_FILE"
trap 'rm -f "$STATE_FILE"' EXIT

# Create helper scripts for navigation
NAV_UP_SCRIPT=$(mktemp)
NAV_DOWN_SCRIPT=$(mktemp)
trap 'rm -f "$STATE_FILE" "$NAV_UP_SCRIPT" "$NAV_DOWN_SCRIPT"' EXIT

# Script to navigate up
cat > "$NAV_UP_SCRIPT" << 'EOF'
#!/bin/bash
STATE_FILE="$1"
cur=$(cat "$STATE_FILE" 2>/dev/null || echo "$HOME")
if [[ "$cur" != "/" && "$cur" != "$HOME" ]]; then
    parent=$(dirname "$cur")
    echo "$parent" > "$STATE_FILE"
    find "$parent" -maxdepth 1 -type d -not -path '*/.*' 2>/dev/null | sort
else
    find "$cur" -maxdepth 1 -type d -not -path '*/.*' 2>/dev/null | sort
fi
EOF

# Script to navigate down
cat > "$NAV_DOWN_SCRIPT" << 'EOF'
#!/bin/bash
STATE_FILE="$1"
selected="$2"
if [[ -n "$selected" && -d "$selected" ]]; then
    echo "$selected" > "$STATE_FILE"
    find "$selected" -maxdepth 1 -type d -not -path '*/.*' 2>/dev/null | sort
else
    cur=$(cat "$STATE_FILE" 2>/dev/null || echo "$HOME")
    find "$cur" -maxdepth 1 -type d -not -path '*/.*' 2>/dev/null | sort
fi
EOF

chmod +x "$NAV_UP_SCRIPT" "$NAV_DOWN_SCRIPT"

# ------------------------------------------------------------------
#  FZF configuration
# ------------------------------------------------------------------
fzf_args=(
    --multi                               # allow multi‑selection
    --query "${DEFAULT_DIR}"
    --preview 'ls -ltr {}'
    --preview-label='alt-o: Go Up One Level, alt-i: Go Into Selected Folder'
    --preview-label-pos=bottom
    --preview-window 'down:65%:wrap'

    # Bindings -------------------------------------------------------
    # Alt-O: Go up one directory level and reload
    --bind "alt-o:reload($NAV_UP_SCRIPT $STATE_FILE)"
    # Alt-I: Go into the currently selected directory and reload
    --bind "alt-i:reload($NAV_DOWN_SCRIPT $STATE_FILE {})"

    # Additional navigation inside preview pane
    --bind 'alt-u:preview-half-page-up'
    --bind 'alt-d:preview-half-page-down'

    # Colours -------------------------------------------------------
    --color pointer:green,marker:green
)

# ------------------------------------------------------------------
#  Find candidate directories (top‑level only)
# ------------------------------------------------------------------
target_paths=$(find ~ -type d -not -path '*/.*' 2>/dev/null | sort | fzf "${fzf_args[@]}" || true)

# ------------------------------------------------------------------
#  Run fileup on each chosen directory
# ------------------------------------------------------------------
if [[ -n "$target_paths" ]]; then
    # Convert newline‑separated selections to space‑separated for yay
    echo "Selected: $target_paths"

    go-fifimove \
        -config="$BASE_PATH/script/env_file/Paths_fifimove.yaml" \
        -log="$BASE_PATH/Documents/log_script/fifimove-log-$(date '+%Y%m%d%H%M').log" \
        -src=$target_paths

    omarchy-show-done
fi

