#!/bin/bash
# OHIF Viewer Setup Script for Django Integration
# Usage: ./setup-ohif.sh

set -e

echo "=== OHIF Viewer Setup ==="

# 1. Install bun if not available
if ! command -v bun &> /dev/null; then
    echo "Installing bun..."
    curl -fsSL https://bun.sh/install | bash
fi

# Add bun to PATH
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# 2. Install dependencies
echo "Installing dependencies..."
cd viewer
bun install

# 3. Build for production
echo "Building OHIF (this may take 15-30 minutes)..."
export PUBLIC_URL=/ohif/
bun run build

# 4. Create Django static directory
echo "Copying build to Django static files..."
mkdir -p ../telemedvision/static/ohif
cp -r platform/app/dist/* ../telemedvision/static/ohif/

echo "=== Setup Complete ==="
echo ""
echo "To start dev server:"
echo "  cd viewer/platform/app && PUBLIC_URL=/ohif/ bun run dev:fast"
echo ""
echo "To access OHIF in Django, add to urls.py:"
echo "  path('ohif/', RedirectView.as_view(url='/static/ohif/index.html'))"
