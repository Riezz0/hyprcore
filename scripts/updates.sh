#!/bin/bash

# A script to check for updates from Pacman, YAY (AUR), and Flatpak
# and output the total count for Waybar.

# --- Configuration ---
PACMAN_ICON="<span font='20px'>󰮯</span>"      # Package Icon (Nerd Font - customize as needed)
AUR_ICON="<span font='20px'></span>"         # AUR Icon (Nerd Font)
FLATPAK_ICON="<span font='20px'></span>"     # Flatpak Icon (Nerd Font)
NO_UPDATES_ICON="<span font='20px'>󰂪</span>"  # Up-to-date Icon (Nerd Font)

# --- Update Check Functions ---

# Check Pacman official repositories (requires pacman-contrib for checkupdates)
count_pacman() {
    # checkupdates: Lists official repository updates
    if command -v checkupdates &> /dev/null; then
        checkupdates 2>/dev/null | wc -l
    else
        # Fallback to pacman -Qu, less safe as it touches the main DB
        # Only use if you understand the risks
        # pacman -Qu 2>/dev/null | wc -l
        echo "0"
    fi
}

# Check AUR/Yay updates
count_yay() {
    # yay -Qu: Lists AUR updates (and sometimes Pacman, but checkupdates handles the main ones)
    if command -v yay &> /dev/null; then
        yay -Qu --aur --quiet 2>/dev/null | wc -l
    else
        echo "0"
    fi
}

# Check Flatpak updates
count_flatpak() {
    # flatpak remote-ls --updates: Lists available Flatpak updates
    if command -v flatpak &> /dev/null; then
        flatpak remote-ls --updates 2>/dev/null | grep -c "flatpak"
    else
        echo "0"
    fi
}

# --- Main Logic ---

PACMAN_COUNT=$(count_pacman)
YAY_COUNT=$(count_yay)
FLATPAK_COUNT=$(count_flatpak)

TOTAL_COUNT=$((PACMAN_COUNT + YAY_COUNT + FLATPAK_COUNT))

# --- Output for Waybar ---

if [ "$TOTAL_COUNT" -gt 0 ]; then
    # Format the output when updates are available
    TEXT="${PACMAN_COUNT} ${PACMAN_ICON}"
    if [ "$YAY_COUNT" -gt 0 ]; then
        TEXT="${TEXT} ${YAY_COUNT} ${AUR_ICON}"
    fi
    if [ "$FLATPAK_COUNT" -gt 0 ]; then
        TEXT="${TEXT} ${FLATPAK_COUNT} ${FLATPAK_ICON}"
    fi
    
    # Waybar expects a single string for 'text'
    # We will use the 'critical' class for styling when updates are present
    echo "{\"text\": \"${TEXT}\", \"class\": \"updates-available\", \"tooltip\": \"Pacman: ${PACMAN_COUNT}\nAUR: ${YAY_COUNT}\nFlatpak: ${FLATPAK_COUNT}\"}"
else
    # Output when no updates are available
    echo "{\"text\": \"${NO_UPDATES_ICON}\", \"class\": \"all-updated\", \"tooltip\": \"System is up to date.\"}"
fi
