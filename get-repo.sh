#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_substep() {
    echo -e "  ${BLUE}→${NC} $1"
}

# Configuration
CONFIG_FILE="$HOME/.config/hypr/hyprland.conf"
SOURCE_LINE="source = ~/.config/hypr/HxA.conf"
CONFIG_DIR="$HOME/.config/hypr"
DOTS_DIR="$HOME/dots"

log_info "Starting Hyprland configuration setup..."

# Section 1: Hyprland configuration
log_info "Configuring Hyprland..."

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log_warning "Configuration file not found at $CONFIG_FILE"
    log_substep "Creating directory and basic config file..."
    mkdir -p "$CONFIG_DIR"
    echo "# Hyprland Configuration" > "$CONFIG_FILE"
    echo "# Generated on $(date)" >> "$CONFIG_FILE"
    log_success "Created basic hyprland.conf"
fi

# Check if source line already exists
if grep -q "source.*HxA.conf" "$CONFIG_FILE"; then
    log_warning "HxA.conf source directive already exists in the configuration."
    echo -n "Would you like to update it? [y/N]: "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Keeping existing configuration."
    else
        # Remove existing HxA.conf source line
        sed -i '/source.*HxA.conf/d' "$CONFIG_FILE"
        log_success "Removed existing HxA.conf source directive."
    fi
fi

# Only add if it doesn't exist (or was removed)
if ! grep -q "source.*HxA.conf" "$CONFIG_FILE"; then
    # Create HxA.conf if it doesn't exist
    if [ ! -f "$CONFIG_DIR/HxA.conf" ]; then
        log_substep "Creating HxA.conf with default HxA.py window rules..."
        cat > "$CONFIG_DIR/HxA.conf" << 'EOF'
# HxA.py window rules
windowrulev2 = float, class:^(HxA.py)$
windowrulev2 = center 1, class:^(HxA.py)$
windowrulev2 = bordersize 2, class:^(HxA.py)$
windowrulev2 = opacity override 0.8, fullscreen:0, class:^(HxA.py)$
windowrulev2 = opacity override 0.8, fullscreen:1, class:^(HxA.py)$
EOF
        log_success "Created $CONFIG_DIR/HxA.conf"
    fi

    # Find the best place to insert the source directive
    # Try to insert after the last source line
    LAST_SOURCE_LINE=$(grep -n "^source\s*=" "$CONFIG_FILE" | tail -1 | cut -d: -f1)

    if [ -n "$LAST_SOURCE_LINE" ]; then
        # Insert after the last source line
        sed -i "${LAST_SOURCE_LINE}a $SOURCE_LINE" "$CONFIG_FILE"
        log_success "Added source directive after existing source directives"
    else
        # Try to insert after the initial section (usually after the first few lines)
        # Look for common initial config sections
        INITIAL_SECTIONS=$(grep -n "^\s*\(#\|$\)" "$CONFIG_FILE" | tail -5 | cut -d: -f1 | head -1)
        
        if [ -n "$INITIAL_SECTIONS" ] && [ "$INITIAL_SECTIONS" -gt 0 ]; then
            sed -i "${INITIAL_SECTIONS}a $SOURCE_LINE" "$CONFIG_FILE"
            log_success "Added source directive after initial configuration section"
        else
            # Append to the end of file as fallback
            echo -e "\n$SOURCE_LINE" >> "$CONFIG_FILE"
            log_success "Added source directive to the end of the configuration file"
        fi
    fi
fi

log_success "Hyprland configuration updated"

# Section 2: Install yay if needed
log_info "Checking for yay installation..."

if ! command -v yay &> /dev/null; then
    log_substep "Installing yay..."
    
    # Check if we're on Arch Linux
    if ! command -v pacman &> /dev/null; then
        log_error "This script requires Arch Linux or an Arch-based distribution"
        exit 1
    fi
    
    # Install required packages
    log_substep "Installing required packages..."
    sudo pacman -S --needed --noconfirm git base-devel
    
    # Install yay from AUR
    log_substep "Building yay from AUR..."
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    cd /tmp/yay || { log_error "Failed to cd to /tmp/yay"; exit 1; }
    makepkg -si --noconfirm
    cd ~ || exit 1
    
    # Verify installation
    if command -v yay &> /dev/null; then
        log_success "yay installed successfully"
    else
        log_error "Failed to install yay"
        exit 1
    fi
else
    log_success "yay already installed"
fi

# Section 3: Install required packages
log_info "Installing required packages..."

# Install python-gobject and xfce-polkit
log_substep "Installing python-gobject and xfce-polkit..."
if yay -S --noconfirm python-gobject xfce-polkit; then
    log_success "Packages installed successfully"
else
    log_warning "Failed to install packages with yay, trying with pacman..."
    sudo pacman -S --noconfirm python-gobject polkit
fi

# Section 4: Clone repository
log_info "Setting up HxA application..."

if [ -d "$DOTS_DIR" ]; then
    log_warning "Directory $DOTS_DIR already exists"
    echo -n "Would you like to remove it and clone fresh? [y/N]: "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_substep "Removing existing directory..."
        rm -rf "$DOTS_DIR"
    else
        log_substep "Updating existing repository..."
        cd "$DOTS_DIR" && git pull
    fi
fi

if [ ! -d "$DOTS_DIR" ]; then
    log_substep "Cloning repository..."
    if git clone https://github.com/Riezz0/hyprcore.git "$DOTS_DIR"; then
        log_success "Repository cloned successfully"
    else
        log_error "Failed to clone repository"
        exit 1
    fi
fi

# Section 5: Make script executable and run
log_info "Setting up HxA.py..."

if [ -f "$DOTS_DIR/HxA.py" ]; then
    log_substep "Making HxA.py executable..."
    chmod +x "$DOTS_DIR/HxA.py"
    
    # Reload Hyprland if it's running
    if command -v hyprctl &> /dev/null && [ -n "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
        log_substep "Reloading Hyprland..."
        if hyprctl reload; then
            log_success "Hyprland reloaded successfully"
        else
            log_warning "Failed to reload Hyprland"
        fi
    else
        log_info "Hyprland not running or hyprctl not available"
        log_info "Changes will take effect after Hyprland restart"
    fi
    
    # Ask if user wants to run HxA.py
    echo ""
    log_info "Setup complete!"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. The HxA.py application is ready at: $DOTS_DIR/HxA.py"
    echo "2. Hyprland configuration has been updated"
    echo "3. Required packages are installed"
    echo ""
    echo -n "Would you like to run HxA.py now? [y/N]: "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_substep "Running HxA.py..."
        cd "$DOTS_DIR" && python3 HxA.py
    else
        log_info "You can run it later with: cd $DOTS_DIR && python3 HxA.py"
    fi
else
    log_error "HxA.py not found in $DOTS_DIR"
    log_info "Please check the repository contents manually"
    exit 1
fi

log_success "Setup completed successfully!"
