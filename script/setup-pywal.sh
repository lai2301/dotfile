#!/bin/bash
# Setup pywal for dynamic color schemes

echo "Installing pywal..."
pip install --user pywal

echo "Creating wal directory..."
mkdir -p ~/.cache/wal

echo "Generating colors from current wallpaper..."
# Find current wallpaper (adjust path as needed)
WALLPAPER=$(find ~/Pictures -name "*.jpg" -o -name "*.png" | head -1)

if [ -n "$WALLPAPER" ]; then
    wal -i "$WALLPAPER"
    echo "✓ Colors generated from: $WALLPAPER"
else
    echo "No wallpaper found. Run manually: wal -i /path/to/your/wallpaper.jpg"
fi

echo "✓ Pywal setup complete!"
echo "Run 'wal -i /path/to/image' to generate colors from any image"

