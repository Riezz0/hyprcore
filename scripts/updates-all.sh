#!/usr/bin/env bash

# Function to check for updates
check_updates() {
    local pacman_updates=0
    local flatpak_updates=0
    local total_updates=0
    
    # Check for pacman/AUR updates using yay
    if command -v yay &> /dev/null; then
        # Use --quiet flag to only show update count
        pacman_updates=$(yay -Qu 2>/dev/null | grep -v "忽略的" | grep -v "忽略" | wc -l)
    fi
    
    # Check for Flatpak updates
    if command -v flatpak &> /dev/null; then
        flatpak_updates=$(flatpak remote-ls --updates 2>/dev/null | wc -l)
    fi
    
    total_updates=$((pacman_updates + flatpak_updates))
    
    # Prepare tooltip text
    local tooltip=""
    if [ $pacman_updates -gt 0 ] && [ $flatpak_updates -gt 0 ]; then
        tooltip="Pacman/AUR: $pacman_updates\nFlatpak: $flatpak_updates"
    elif [ $pacman_updates -gt 0 ]; then
        tooltip="Pacman/AUR: $pacman_updates"
    elif [ $flatpak_updates -gt 0 ]; then
        tooltip="Flatpak: $flatpak_updates"
    else
        tooltip="System is up to date"
    fi
    
    # Output JSON for Waybar
    if [ $total_updates -gt 0 ]; then
        echo "{\"text\": \"󰏗 $total_updates\", \"alt\": \"󰚰 Updates: $total_updates\", \"tooltip\": \"$tooltip\", \"class\": \"updates-available\"}"
    else
        echo "{\"text\": \"󰄲\", \"alt\": \"󰄲 Updated\", \"tooltip\": \"$tooltip\", \"class\": \"no-updates\"}"
    fi
}

# Create cache directory
CACHE_DIR="$HOME/.cache/waybar-updates"
CACHE_FILE="$CACHE_DIR/last_check"
mkdir -p "$CACHE_DIR"

# Force update check if --force flag is passed
if [[ "$1" == "--force" ]]; then
    check_updates
    exit 0
fi

# Check cache (5 minutes)
if [ -f "$CACHE_FILE" ]; then
    last_check=$(cat "$CACHE_FILE")
    current_time=$(date +%s)
    if [ $((current_time - last_check)) -lt 300 ]; then
        # Read cached count if exists
        if [ -f "$CACHE_DIR/count" ]; then
            read -r cached_total cached_pacman cached_flatpak < "$CACHE_DIR/count"
            if [ $cached_total -gt 0 ]; then
                echo "{\"text\": \"󰏗 $cached_total\", \"alt\": \"󰚰 Updates: $cached_total\", \"tooltip\": \"Pacman/AUR: $cached_pacman\nFlatpak: $cached_flatpak\", \"class\": \"updates-available\"}"
            else
                echo "{\"text\": \"󰄲\", \"alt\": \"󰄲 Updated\", \"tooltip\": \"System is up to date\", \"class\": \"no-updates\"}"
            fi
            exit 0
        fi
    fi
fi

# Perform new check
check_updates
