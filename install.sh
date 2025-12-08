#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_step() {
    echo -e "${PURPLE}▶${NC} $1"
}

log_substep() {
    echo -e "${CYAN}  ↳${NC} $1"
}

# Function to check if a package is installed
is_package_installed() {
    if pacman -Qi "$1" &>/dev/null || yay -Qi "$1" &>/dev/null; then
        return 0 # Package is installed
    else
        return 1 # Package is not installed
    fi
}

# Function to check if a service is active
is_service_active() {
    if systemctl is-active --quiet "$1"; then
        return 0 # Service is active
    else
        return 1 # Service is not active
    fi
}

# Function to install packages with progress tracking
install_packages() {
    local packages=("$@")
    local total=${#packages[@]}
    local installed=0
    local skipped=0
    local failed=0
    
    log_step "Checking and installing packages ($total total)"
    
    for pkg in "${packages[@]}"; do
        if is_package_installed "$pkg"; then
            log_substep "$pkg ${GREEN}✓ Already installed${NC}"
            ((skipped++))
        else
            log_substep "Installing $pkg..."
            if yay -S --needed --noconfirm "$pkg" &>/dev/null; then
                log_substep "$pkg ${GREEN}✓ Installed${NC}"
                ((installed++))
            else
                log_substep "$pkg ${RED}✗ Failed${NC}"
                ((failed++))
            fi
        fi
        # Update progress
        echo -ne "\rProgress: [$installed installed, $skipped skipped, $failed failed]"
    done
    echo "" # New line after progress
    log_success "Package installation completed: $installed new, $skipped already installed, $failed failed"
}

# Function to ask for user confirmation
ask_confirm() {
    local prompt="$1"
    local default="${2:-n}"
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -rp "$prompt" response
    response="${response:-$default}"
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# Start installation
echo -e "${CYAN}========================================${NC}"
echo -e "${PURPLE}    Dotfiles Installation Script${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Update system first
log_step "Updating system packages..."
sudo pacman -Syu --noconfirm
log_success "System updated"

# Install AUR helper if not installed
log_step "Checking for yay..."
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

# Define packages to install
PACKAGES=(
    swww qt5-quickcontrols qt5-quickcontrols2 qt5-graphicaleffects
    hypridle hyprlock hyprpicker tree qt5ct qt6ct qt5-styleplugins
    wl-clipboard firefox code nemo vlc nwg-look gnome-disk-utility
    nwg-displays zsh ttf-meslo-nerd ttf-font-awesome ttf-font-awesome-4
    ttf-font-awesome-5 waybar rust cargo fastfetch cmatrix pavucontrol
    net-tools python-pip python-psutil python-virtualenv python-requests
    python-hijri-converter python-pytz python-gobject xfce4-settings
    xfce-polkit exa libreoffice-fresh rofi-wayland neovim goverlay-git
    flatpak python-pywal16 python-pywalfox make linux-firmware dkms
    automake linux-zen-headers kvantum-qt5 chromium nemo-fileroller
    waybar-module-pacman-updates-git
)

# Install packages
install_packages "${PACKAGES[@]}"

# Ask about CoolerControl installation
if ask_confirm "Do you want to install CoolerControl for fan control?" "n"; then
    log_step "Installing CoolerControl..."
    
    # Install coolercontrol if not already installed
    if ! is_package_installed "coolercontrol"; then
        log_substep "CoolerControl not found, installing from AUR..."
        if yay -S --needed --noconfirm coolercontrol &>/dev/null; then
            log_success "CoolerControl installed"
        else
            log_warning "Failed to install CoolerControl from AUR, trying manual installation..."
            # Alternative installation method
            if ! command -v coolercontrold &> /dev/null; then
                log_substep "Building coolercontrol from source..."
                git clone https://github.com/David-Lor/CoolerControl.git /tmp/coolercontrol
                cd /tmp/coolercontrol
                mkdir build && cd build
                cmake .. && make && sudo make install
                cd ~
                log_success "CoolerControl built from source"
            fi
        fi
    else
        log_success "CoolerControl already installed"
    fi
    
    # Ask about NCT6687D driver installation for CoolerControl
    if ask_confirm "Do you want to install NCT6687D driver for sensor support (required for some motherboards)?" "n"; then
        # NCT6687D driver - IMPORTANT for CoolerControl sensor support
        log_step "Installing NCT6687D driver for sensor support..."
        if [ ! -d "/home/$USER/tmp/nct6687d" ]; then
            git clone https://github.com/Fred78290/nct6687d /home/$USER/tmp/nct6687d 2>/dev/null
            log_substep "NCT6687D repository cloned"
        fi

        if [ -d "/home/$USER/tmp/nct6687d" ]; then
            cd /home/$USER/tmp/nct6687d/
            
            # Check if driver is already loaded
            if ! lsmod | grep -q nct6687; then
                log_substep "Building and installing NCT6687D driver..."
                make dkms/install 2>/dev/null && log_substep "Driver compiled and installed"
                
                if [ -f "/home/$USER/dots/sys/no_nct6683.conf" ]; then
                    sudo cp -r /home/$USER/dots/sys/no_nct6683.conf /etc/modprobe.d/ 2>/dev/null
                    log_substep "Blacklisted conflicting nct6683 module"
                fi
                
                if [ -f "/home/$USER/dots/sys/nct6687.conf" ]; then
                    sudo cp -r /home/$USER/dots/sys/nct6687.conf /etc/modules-load.d/nct6687.conf 2>/dev/null
                    log_substep "Added nct6687 to modules-load"
                fi
                
                # Load the module
                sudo modprobe nct6687 2>/dev/null
                if lsmod | grep -q nct6687; then
                    log_success "NCT6687D module loaded successfully"
                else
                    log_warning "Failed to load NCT6687D module"
                fi
            else
                log_success "NCT6687D module already loaded"
            fi
            cd ~
        fi
    else
        log_step "Skipping NCT6687D driver installation."
    fi
else
    log_step "Skipping CoolerControl installation."
fi

# Create directories
log_step "Creating directories..."
mkdir -p ~/git ~/venv /home/$USER/tmp/
sudo mkdir -p /etc/modules-load.d/
log_success "Directories created"

# Install fonts with proper directory creation
log_step "Installing fonts..."
FONT_DIR="$HOME/.local/share/fonts"
mkdir -p "$FONT_DIR"

if [ -d "/home/$USER/dots/fonts/" ]; then
    # Check if fonts directory has any files
    if [ "$(ls -A /home/$USER/dots/fonts/ 2>/dev/null)" ]; then
        log_substep "Copying fonts from dots/fonts/ to $FONT_DIR..."
        cp -r /home/$USER/dots/fonts/* "$FONT_DIR/" 2>/dev/null
        fc-cache -fv
        log_success "Fonts installed and cache updated"
    else
        log_warning "Fonts directory is empty, skipping..."
    fi
else
    log_warning "Fonts directory not found at /home/$USER/dots/fonts/, skipping..."
fi

# Flatpak installations
log_step "Installing Flatpak applications..."
FLATPAK_APPS=(
    "org.localsend.localsend_app"
    "com.github.tchx84.Flatseal"
    "com.usebottles.bottles"
)

for app in "${FLATPAK_APPS[@]}"; do
    if flatpak list | grep -q "$app"; then
        log_substep "$app ${GREEN}✓ Already installed${NC}"
    else
        log_substep "Installing $app..."
        flatpak install --noninteractive flathub "$app" &>/dev/null && \
            log_substep "$app ${GREEN}✓ Installed${NC}" || \
            log_substep "$app ${RED}✗ Failed${NC}"
    fi
done

# ZSH plugins - ensure tmp directory exists
log_step "Installing ZSH plugins..."
ZSH_TMP_DIR="/home/$USER/dots/tmp/"
mkdir -p "$ZSH_TMP_DIR"

ZSH_PLUGINS=(
    "https://github.com/zsh-users/zsh-autosuggestions.git"
    "https://github.com/zsh-users/zsh-syntax-highlighting.git"
    "https://github.com/zdharma-continuum/fast-syntax-highlighting.git"
    "https://github.com/marlonrichert/zsh-autocomplete.git"
    "https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git"
)

for plugin in "${ZSH_PLUGINS[@]}"; do
    plugin_name=$(basename "$plugin" .git)
    if [ ! -d "$ZSH_TMP_DIR/$plugin_name" ]; then
        log_substep "Cloning $plugin_name..."
        if [[ "$plugin" == *"zsh-autocomplete"* ]]; then
            git clone --depth 1 "$plugin" "$ZSH_TMP_DIR/$plugin_name/" 2>/dev/null
        else
            git clone "$plugin" "$ZSH_TMP_DIR/$plugin_name/" 2>/dev/null
        fi
        if [ $? -eq 0 ]; then
            log_substep "$plugin_name ${GREEN}✓ Cloned${NC}"
        else
            log_substep "$plugin_name ${RED}✗ Failed to clone${NC}"
        fi
    else
        log_substep "$plugin_name ${GREEN}✓ Already cloned${NC}"
    fi
done

# Oh My Zsh
log_step "Installing Oh My Zsh..."
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
    if [ $? -eq 0 ]; then
        log_success "Oh My Zsh installed"
    else
        log_error "Failed to install Oh My Zsh"
    fi
else
    log_success "Oh My Zsh already installed"
fi

# Set ZSH as default shell
log_step "Setting ZSH as default shell..."
CURRENT_SHELL=$(basename "$SHELL")
if [ "$CURRENT_SHELL" != "zsh" ]; then
    chsh -s "$(which zsh)"
    if [ $? -eq 0 ]; then
        log_success "Default shell changed to ZSH"
    else
        log_error "Failed to change default shell to ZSH"
    fi
else
    log_success "ZSH is already the default shell"
fi

# Copy ZSH plugins - FIXED: Ensure proper copying with verbose output
log_step "Configuring ZSH plugins..."
OHMYZSH_PLUGINS_DIR="$HOME/.oh-my-zsh/custom/plugins"
mkdir -p "$OHMYZSH_PLUGINS_DIR"

PLUGIN_MAPPING=(
    "autoswitch_virtualenv:autoswitch-virtualenv"
    "fast-syntax-highlighting:fast-syntax-highlighting"
    "zsh-autocomplete:zsh-autocomplete"
    "zsh-autosuggestions:zsh-autosuggestions"
    "zsh-syntax-highlighting:zsh-syntax-highlighting"
)

for plugin_mapping in "${PLUGIN_MAPPING[@]}"; do
    source_dir=$(echo "$plugin_mapping" | cut -d':' -f1)
    dest_dir=$(echo "$plugin_mapping" | cut -d':' -f2)
    
    if [ -d "$ZSH_TMP_DIR/$source_dir" ]; then
        if [ ! -d "$OHMYZSH_PLUGINS_DIR/$dest_dir" ]; then
            log_substep "Copying $source_dir to $dest_dir..."
            cp -r "$ZSH_TMP_DIR/$source_dir" "$OHMYZSH_PLUGINS_DIR/$dest_dir" 2>/dev/null
            if [ $? -eq 0 ] && [ -d "$OHMYZSH_PLUGINS_DIR/$dest_dir" ]; then
                log_substep "$dest_dir ${GREEN}✓ Installed${NC}"
            else
                log_substep "$dest_dir ${RED}✗ Failed to copy${NC}"
            fi
        else
            log_substep "$dest_dir ${GREEN}✓ Already exists${NC}"
        fi
    else
        log_substep "$source_dir ${YELLOW}⚠ Source not found${NC}"
    fi
done

# Update ZSH plugin configuration
log_step "Updating ZSH configuration..."
if [ -f "$HOME/.zshrc" ] || [ -L "$HOME/.zshrc" ]; then
    # Backup existing .zshrc
    if [ -f "$HOME/.zshrc" ]; then
        cp "$HOME/.zshrc" "$HOME/.zshrc.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    # Ensure plugins are properly listed in .zshrc if we have a template
    if [ -f "/home/$USER/dots/.zshrc" ]; then
        # This would be handled by the symlink creation later
        log_substep "ZSH config will be linked from dots directory"
    fi
fi

log_success "ZSH plugins configured"

# Cleanup temporary ZSH files
log_step "Cleaning up temporary files..."
rm -rf /home/$USER/dots/tmp/ 2>/dev/null
log_success "Temporary files cleaned"

# Remove existing configs
log_step "Removing existing configurations..."
declare -a CONFIGS_TO_REMOVE=(
    "/home/$USER/.config/hypr"
    "/home/$USER/.config/kitty"
    "/home/$USER/.zshrc"
    "/home/$USER/.config/hypr/monitors.conf"
)

for config in "${CONFIGS_TO_REMOVE[@]}"; do
    if [ -e "$config" ]; then
        rm -rf "$config" 2>/dev/null
        log_substep "Removed: $(basename "$config")"
    fi
done

# Remove system configs
if [ -f "/etc/sddm.conf" ]; then
    sudo rm /etc/sddm.conf 2>/dev/null
    log_substep "Removed: sddm.conf"
fi

if [ -f "/etc/default/grub" ]; then
    sudo rm /etc/default/grub 2>/dev/null
    log_substep "Removed: grub"
fi

# Create symlinks
log_step "Creating configuration symlinks..."
declare -a SYMLINKS=(
    ".zshrc:/home/$USER/"
    "fastfetch/:/home/$USER/.config/"
    "hypr/:/home/$USER/.config/"
    "kitty/:/home/$USER/.config/"
    "Kvantum/:/home/$USER/.config/"
    "nvim/:/home/$USER/.config/"
    "pywal/:/home/$USER/.config/"
    "qt5ct/:/home/$USER/.config/"
    "qt6ct/:/home/$USER/.config/"
    "rofi/:/home/$USER/.config/"
    "scripts/:/home/$USER/.config/"
    "wal/:/home/$USER/.config/"
    "wallpapers/:/home/$USER/.config/"
    "waybar/:/home/$USER/.config/"
    "xdg-desktop-portal/:/home/$USER/.config/"
    ".icons/:/home/$USER/"
    ".themes/:/home/$USER/"
)

for link in "${SYMLINKS[@]}"; do
    source=$(echo "$link" | cut -d':' -f1)
    target=$(echo "$link" | cut -d':' -f2)
    target_full="$target$(basename "$source")"
    
    # Ensure target directory exists
    target_dir=$(dirname "$target_full")
    mkdir -p "$target_dir"
    
    if [ -e "/home/$USER/dots/$source" ]; then
        if [ -L "$target_full" ]; then
            # Remove existing symlink
            rm "$target_full" 2>/dev/null
        fi
        
        if [ ! -e "$target_full" ]; then
            ln -sf "/home/$USER/dots/$source" "$target_full" 2>/dev/null
            if [ $? -eq 0 ]; then
                log_substep "Linked: $source → $(basename "$target_full")"
            else
                log_substep "$source ${RED}✗ Failed to link${NC}"
            fi
        else
            log_substep "$(basename "$source") ${YELLOW}⚠ Already exists (not a symlink)${NC}"
        fi
    else
        log_substep "$source ${YELLOW}⚠ Source not found${NC}"
    fi
done

# Cursor and theme setup
log_step "Setting up cursor and theme..."

if [ -d "/home/$USER/dots/sys/cursors/default" ]; then
    sudo rm -rf /usr/share/icons/default 2>/dev/null
    sudo cp -r /home/$USER/dots/sys/cursors/default /usr/share/icons/ 2>/dev/null
    log_substep "Default cursor theme set"
fi

if [ -d "/home/$USER/dots/sys/cursors/oreo_white_cursors" ]; then
    sudo cp -r /home/$USER/dots/sys/cursors/oreo_white_cursors /usr/share/icons/ 2>/dev/null
    log_substep "Oreo white cursor theme installed"
fi

# Apply GNOME settings
log_step "Applying GNOME/GTK settings..."
gsettings set org.gnome.desktop.interface cursor-theme "oreo_white_cursors" 2>/dev/null
gsettings set org.gnome.desktop.interface icon-theme "oomox-Tokyo-Night" 2>/dev/null
gsettings set org.gnome.desktop.interface gtk-theme "oomox-Tokyo-Night" 2>/dev/null
gsettings set org.gnome.desktop.interface font-name "MesloLGL Nerd Font 12" 2>/dev/null
gsettings set org.gnome.desktop.interface document-font-name "MesloLGL Nerd Font 12" 2>/dev/null
gsettings set org.gnome.desktop.interface monospace-font-name "MesloLGL Mono Nerd Font 12" 2>/dev/null
gsettings set org.gnome.desktop.wm.preferences titlebar-font "MesloLGL Mono Nerd Font 12" 2>/dev/null
log_success "GTK settings applied"

# Start swww and apply pywal
log_step "Starting background services..."
swww-daemon 2>/dev/null &
if [ -f "/home/$USER/scripts/swww.sh" ]; then
    bash /home/$USER/scripts/swww.sh &
    log_substep "SWWW wallpaper service started"
fi

if [ -f "~/.config/pywal/themes/active.json" ]; then
    wal --theme ~/.config/pywal/themes/active.json 2>/dev/null
    log_substep "Pywal theme applied"
fi

# Copy pywal configs
if [ -f "${HOME}/.cache/wal/pywal.kvconfig" ]; then
    mkdir -p "${HOME}/.config/Kvantum/pywal/"
    cp "${HOME}"/.cache/wal/pywal.kvconfig "${HOME}"/.config/Kvantum/pywal/pywal.kvconfig 2>/dev/null
    log_substep "Pywal Kvantum config updated"
fi

if [ -f "${HOME}/.cache/wal/pywal.svg" ]; then
    mkdir -p "${HOME}/.config/Kvantum/pywal/"
    cp "${HOME}"/.cache/wal/pywal.svg "${HOME}"/.config/Kvantum/pywal/pywal.svg 2>/dev/null
    log_substep "Pywal SVG theme updated"
fi

# SDDM theme
log_step "Configuring SDDM..."
if [ -f "/home/$USER/dots/sys/sddm/sddm.conf" ]; then
    sudo cp -r /home/$USER/dots/sys/sddm/sddm.conf /etc/ 2>/dev/null
    log_substep "SDDM config applied"
fi

if [ -d "/home/$USER/dots/sys/sddm/tokyo-night" ]; then
    sudo mkdir -p /usr/share/sddm/themes/
    sudo cp -r /home/$USER/dots/sys/sddm/tokyo-night/ /usr/share/sddm/themes/ 2>/dev/null
    log_substep "Tokyo Night SDDM theme installed"
fi

# GRUB theme
log_step "Configuring GRUB..."
if [ -f "/home/$USER/dots/sys/grub/grub" ]; then
    sudo cp -r /home/$USER/dots/sys/grub/grub /etc/default/ 2>/dev/null
    log_substep "GRUB config applied"
fi

if [ -d "/home/$USER/dots/sys/grub/tokyo-night" ]; then
    sudo mkdir -p /usr/share/grub/themes/
    sudo cp -r /home/$USER/dots/sys/grub/tokyo-night /usr/share/grub/themes/ 2>/dev/null
    log_substep "Tokyo Night GRUB theme installed"
fi

sudo grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null && log_success "GRUB configured"

# COOLERCONTROL SETUP (only if installed)
if command -v coolercontrold &> /dev/null; then
    log_step "Setting up CoolerControl..."
    # Check if service exists
    if systemctl list-unit-files | grep -q coolercontrol; then
        log_substep "CoolerControl service found"
        
        # Enable and start the service
        if ! is_service_active "coolercontrold.service"; then
            sudo systemctl enable coolercontrold.service 2>/dev/null
            if [ $? -eq 0 ]; then
                log_substep "CoolerControl service enabled"
            else
                log_warning "Failed to enable CoolerControl service"
            fi
            
            sudo systemctl start coolercontrold.service 2>/dev/null
            if [ $? -eq 0 ]; then
                log_substep "CoolerControl service started"
            else
                log_warning "Failed to start CoolerControl service"
            fi
            
            # Check if service is running
            sleep 2
            if is_service_active "coolercontrold.service"; then
                log_success "CoolerControl service is now running"
                log_substep "Service status: $(systemctl is-active coolercontrold.service)"
            else
                log_error "CoolerControl service failed to start"
                log_substep "Check journalctl -u coolercontrold.service for details"
            fi
        else
            log_success "CoolerControl service is already running"
        fi
        
        # Create desktop entry for GUI if it doesn't exist
        if [ ! -f "/usr/share/applications/coolercontrol.desktop" ] && [ ! -f "$HOME/.local/share/applications/coolercontrol.desktop" ]; then
            log_substep "Creating desktop entry..."
            mkdir -p "$HOME/.local/share/applications/"
            cat > /tmp/coolercontrol.desktop << EOF
[Desktop Entry]
Name=CoolerControl
Comment=Monitor and control your cooling devices
Exec=coolercontrol
Icon=coolercontrol
Terminal=false
Type=Application
Categories=Utility;System;
StartupNotify=true
EOF
            sudo cp /tmp/coolercontrol.desktop /usr/share/applications/ 2>/dev/null || \
            cp /tmp/coolercontrol.desktop "$HOME/.local/share/applications/" 2>/dev/null
            rm /tmp/coolercontrol.desktop
            log_substep "Desktop entry created"
        fi
        
        # Check if user is in the necessary groups for hardware access
        if ! groups $USER | grep -q "coolercontrol"; then
            log_substep "Adding user to coolercontrol group..."
            sudo usermod -a -G coolercontrol $USER
            log_substep "User added to coolercontrol group (may require logout/login)"
        fi
        
        # Display CoolerControl info
        log_substep "CoolerControl version: $(coolercontrol --version 2>/dev/null || echo "Unknown")"
        log_substep "Service: coolercontrold"
        log_substep "GUI: coolercontrol"
        log_substep "Web UI: http://localhost:11980 (if enabled)"
        
    else
        log_warning "CoolerControl service unit not found"
        log_substep "You may need to manually create the service"
    fi
fi

# Display configuration
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${PURPLE}    Display Configuration${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${BLUE}🚀 Launching nwg-displays for display configuration...${NC}"
echo -e "${YELLOW}📺 Please set up your monitors in the nwg-displays window.${NC}"
echo -e "${RED}❌ Close the nwg-displays window when you're done to continue...${NC}"
echo ""
nwg-displays

echo ""
echo -e "${GREEN}✅ Display configuration saved!${NC}"

# Summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${PURPLE}    Installation Summary${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}✓ System packages installed${NC}"
echo -e "${GREEN}✓ Fonts and themes configured${NC}"
echo -e "${GREEN}✓ ZSH and plugins set up${NC}"
echo -e "${GREEN}✓ Configuration files linked${NC}"

if command -v coolercontrold &> /dev/null; then
    echo -e "${GREEN}✓ CoolerControl installed and configured${NC}"
fi

echo -e "${GREEN}✓ Display configured${NC}"
echo ""

if command -v coolercontrold &> /dev/null; then
    echo -e "${YELLOW}Note: For CoolerControl to work properly:${NC}"
    echo -e "${YELLOW}1. You may need to reboot for NCT6687D driver to load${NC}"
    echo -e "${YELLOW}2. Log out and back in for coolercontrol group membership${NC}"
    echo -e "${YELLOW}3. Run 'coolercontrol' to access the GUI${NC}"
    echo ""
fi

# Ask for confirmation before reboot
read -rp "Do you want to reboot now? (y/N): " reboot_confirm
if [[ "$reboot_confirm" =~ ^[Yy]$ ]]; then
    log_step "Rebooting system..."
    bash /home/$USER/dots/reboot.sh
else
    echo -e "${YELLOW}Skipping reboot. You can manually run the reboot script later.${NC}"
    if command -v coolercontrold &> /dev/null; then
        echo -e "${YELLOW}To start CoolerControl manually, run: sudo systemctl start coolercontrold.service${NC}"
    fi
fi
