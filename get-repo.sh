#!/bin/bash

# Configuration
CONFIG_FILE="$HOME/.config/hypr/hyprland.conf"
SOURCE_LINE="source = ~/.config/hypr/HxA.conf"
CONFIG_DIR="$HOME/.config/hypr"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found at $CONFIG_FILE"
    echo "Creating directory and basic config file..."
    mkdir -p "$CONFIG_DIR"
    echo "# Hyprland Configuration" > "$CONFIG_FILE"
    echo "# Generated on $(date)" >> "$CONFIG_FILE"
fi

# Check if source line already exists
if grep -q "source.*HxA.conf" "$CONFIG_FILE"; then
    echo "HxA.conf source directive already exists in the configuration."
    echo "Would you like to update it? [y/N]"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Exiting without changes."
        exit 0
    fi
    
    # Remove existing HxA.conf source line
    sed -i '/source.*HxA.conf/d' "$CONFIG_FILE"
    echo "Removed existing HxA.conf source directive."
fi

# Create HxA.conf if it doesn't exist
if [ ! -f "$CONFIG_DIR/HxA.conf" ]; then
    echo "Creating HxA.conf with default HxA.py window rules..."
    cat > "$CONFIG_DIR/HxA.conf" << 'EOF'
# HxA.py window rules
windowrulev2 = float, class:^(HxA.py)$
windowrulev2 = center 1, class:^(HxA.py)$
windowrulev2 = bordersize 2, class:^(HxA.py)$
windowrulev2 = opacity override 0.8, fullscreen:0, class:^(HxA.py)$
windowrulev2 = opacity override 0.8, fullscreen:1, class:^(HxA.py)$
EOF
    echo "Created $CONFIG_DIR/HxA.conf"
fi

# Find the best place to insert the source directive
# Try to insert after the last source line
LAST_SOURCE_LINE=$(grep -n "^source\s*=" "$CONFIG_FILE" | tail -1 | cut -d: -f1)

if [ -n "$LAST_SOURCE_LINE" ]; then
    # Insert after the last source line
    sed -i "${LAST_SOURCE_LINE}a $SOURCE_LINE" "$CONFIG_FILE"
    echo "Added source directive after existing source directives (line $((LAST_SOURCE_LINE + 1)))"
else
    # Try to insert after the initial section (usually after the first few lines)
    # Look for common initial config sections
    INITIAL_SECTIONS=$(grep -n "^\s*\(#\|$\)" "$CONFIG_FILE" | tail -5 | cut -d: -f1 | head -1)
    
    if [ -n "$INITIAL_SECTIONS" ] && [ "$INITIAL_SECTIONS" -gt 0 ]; then
        sed -i "${INITIAL_SECTIONS}a $SOURCE_LINE" "$CONFIG_FILE"
        echo "Added source directive after initial configuration section (line $((INITIAL_SECTIONS + 1)))"
    else
        # Append to the end of file as fallback
        echo -e "\n$SOURCE_LINE" >> "$CONFIG_FILE"
        echo "Added source directive to the end of the configuration file"
    fi
fi

echo "Successfully added: $SOURCE_LINE to $CONFIG_FILE"
echo "Created/Verified HxA.conf file with window rules"

hyprctl reload

if ! command -v yay &> /dev/null; then
    log_substep "Installing yay..."
    sudo pacman -S --needed --noconfirm git base-devel
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    cd /tmp/yay && makepkg -si --noconfirm
    cd ~
    log_success "yay installed"
else
    log_success "yay already installed"
fi

yay -S python-gobject xfce-polkit
git clone https://github.com/Riezz0/hyprcore.git /home/$USER/dots/
chmod +x /home/$USER/dots/HxA.py
cd /home/$USER/dots/ 
python3 /home/$USER/dots/HxA.py
