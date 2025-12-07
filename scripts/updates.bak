#!/bin/bash

# Update AUR and Flatpak packages using zsh
kitty --class=AUR -e zsh -c "
echo '=== Starting system updates ==='

# Update AUR packages
if command -v yay &> /dev/null; then
    echo 'Updating AUR packages with yay...'
    yay -Syyu --noconfirm
    AUR_STATUS=\$?
else
    echo 'yay not found, trying paru...'
    if command -v paru &> /dev/null; then
        paru -Syyu --noconfirm
        AUR_STATUS=\$?
    else
        echo 'No AUR helper found (yay or paru)'
        AUR_STATUS=1
    fi
fi

echo '=== Updating Flatpak ==='

# Update Flatpak packages
if command -v flatpak &> /dev/null; then
    flatpak update -y
    FLATPAK_STATUS=\$?
else
    echo 'flatpak not found'
    FLATPAK_STATUS=1
fi

echo ''
echo '=== Update Summary ==='

if [[ \$AUR_STATUS -eq 0 ]]; then
    echo '✓ AUR updates: Success'
else
    echo '✗ AUR updates: Failed or skipped'
fi

if [[ \$FLATPAK_STATUS -eq 0 ]]; then
    echo '✓ Flatpak updates: Success'
else
    echo '✗ Flatpak updates: Failed or skipped'
fi

echo ''
echo '=== All update operations completed ==='
read '?Press Enter to close this window... '
"
