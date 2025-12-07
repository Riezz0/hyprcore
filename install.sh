#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    echo -e "${CYAN}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

# Function to check if a package is installed
is_package_installed() {
    if command -v yay &>/dev/null; then
        yay -Qi "$1" &>/dev/null 2>&1
    else
        pacman -Qi "$1" &>/dev/null 2>&1
    fi
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &>/dev/null
}

# Function to check if a directory exists
directory_exists() {
    [ -d "$1" ]
}

# Function to check if a file exists
file_exists() {
    [ -f "$1" ]
}

# Function to confirm action
confirm_action() {
    while true; do
        read -rp "$1 (y/n): " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Function to run command with error checking
run_command() {
    local cmd="$1"
    local description="$2"
    
    print_status "$description"
    if eval "$cmd"; then
        print_success "$description completed successfully"
    else
        print_error "$description failed"
        return 1
    fi
}

# Get current user
USER=$(whoami)

# Yay Installation (only if not already installed)
if ! command_exists yay; then
    print_status "Installing yay..."
    if sudo pacman -S --needed git base-devel --noconfirm && \
       git clone https://aur.archlinux.org/yay.git /tmp/yay-install && \
       cd /tmp/yay-install && makepkg -si --noconfirm; then
        print_success "yay installed successfully"
        cd ~ || exit
        rm -rf /tmp/yay-install
    else
        print_error "Failed to install yay"
        exit 1
    fi
else
    print_status "yay is already installed, skipping..."
fi

# Package Installation with checks
packages=(
    swww qt5-quickcontrols qt5-quickcontrols2 qt5-graphicaleffects
    hypridle hyprlock hyprpicker tree qt5ct qt6ct qt5-styleplugins
    wl-clipboard firefox code neemo vlc nwg-look gnome-disk-utility
    nwg-displays zsh ttf-meslo-nerd ttf-font-awesome ttf-font-awesome-4
    ttf-font-awesome-5 waybar rust cargo fastfetch cmatrix pavucontrol
    net-tools python-pip python-psutil python-virtualenv python-requests 
    python-hijri-converter python-pytz python-gobject xfce4-settings 
    xfce-polkit exa libreoffice-fresh rofi-wayland neovim goverlay-git 
    flatpak python-pywal16 python-pywalfox make linux-firmware dkms 
    automake linux-zen-headers kvantum-qt5 chromium
)

# Remove duplicates and non-existent packages
packages=($(printf "%s\n" "${packages[@]}" | sort -u))

to_install=()
for pkg in "${packages[@]}"; do
    if ! is_package_installed "$pkg"; then
        to_install+=("$pkg")
    else
        print_status "Package $pkg is already installed, skipping..."
    fi
done

if [ ${#to_install[@]} -gt 0 ]; then
    print_status "Installing packages: ${to_install[*]}"
    if ! yay -S --needed --noconfirm "${to_install[@]}"; then
        print_warning "Some packages failed to install, continuing..."
    fi
else
    print_status "All packages are already installed."
fi

# OhMyZSH Installation and plugins
ohmyzsh_plugins=(
    "zsh-autosuggestions|https://github.com/zsh-users/zsh-autosuggestions.git"
    "zsh-syntax-highlighting|https://github.com/zsh-users/zsh-syntax-highlighting.git"
    "fast-syntax-highlighting|https://github.com/zdharma-continuum/fast-syntax-highlighting.git"
    "zsh-autocomplete|https://github.com/marlonrichert/zsh-autocomplete.git"
    "autoswitch_virtualenv|https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git"
)

# Create temporary directory if it doesn't exist
tmp_dir="/home/$USER/dots/tmp"
mkdir -p "$tmp_dir"

# Install Oh My Zsh if not already installed
if ! directory_exists "/home/$USER/.oh-my-zsh"; then
    print_status "Installing Oh My Zsh..."
    RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
    if [ $? -eq 0 ]; then
        print_success "Oh My Zsh installed successfully"
    else
        print_error "Failed to install Oh My Zsh"
    fi
else
    print_status "Oh My Zsh is already installed, skipping..."
fi

# Clone and install plugins
for plugin in "${ohmyzsh_plugins[@]}"; do
    IFS='|' read -r plugin_name repo_url <<< "$plugin"
    plugin_tmp_dir="$tmp_dir/$plugin_name"
    plugin_dest_dir="/home/$USER/.oh-my-zsh/custom/plugins/$plugin_name"
    
    if ! directory_exists "$plugin_dest_dir"; then
        print_status "Installing plugin: $plugin_name"
        if directory_exists "$plugin_tmp_dir"; then
            rm -rf "$plugin_tmp_dir"
        fi
        
        if git clone --depth 1 "$repo_url" "$plugin_tmp_dir" 2>/dev/null; then
            mkdir -p "/home/$USER/.oh-my-zsh/custom/plugins/"
            cp -r "$plugin_tmp_dir" "/home/$USER/.oh-my-zsh/custom/plugins/"
            print_success "Successfully installed $plugin_name"
        else
            print_error "Failed to clone $plugin_name"
        fi
    else
        print_status "Plugin $plugin_name is already installed, skipping..."
    fi
done

# Change shell to zsh if not already
current_shell=$(basename "$SHELL")
if [ "$current_shell" != "zsh" ]; then
    print_status "Changing shell to zsh..."
    if command_exists zsh; then
        zsh_path=$(which zsh)
        if sudo chsh -s "$zsh_path" "$USER"; then
            print_success "Shell changed to zsh"
        else
            print_error "Failed to change shell to zsh"
        fi
    else
        print_error "zsh not found, cannot change shell"
    fi
else
    print_status "zsh is already the default shell, skipping..."
fi

# Create symlink for .zshrc if it doesn't exist
zshrc_source="/home/$USER/dots/.zshrc"
zshrc_dest="/home/$USER/.zshrc"

if file_exists "$zshrc_source"; then
    if [ ! -L "$zshrc_dest" ] || [ ! -f "$zshrc_dest" ]; then
        print_status "Creating .zshrc symlink..."
        if [ -f "$zshrc_dest" ] || [ -L "$zshrc_dest" ]; then
            rm -f "$zshrc_dest"
        fi
        if ln -sf "$zshrc_source" "$zshrc_dest"; then
            print_success ".zshrc symlink created"
        else
            print_error "Failed to create .zshrc symlink"
        fi
    else
        print_status ".zshrc already exists, skipping..."
    fi
else
    print_warning "Source .zshrc not found at $zshrc_source"
fi

# Clean up temporary directory
if directory_exists "$tmp_dir"; then
    print_status "Cleaning up temporary directory..."
    rm -rf "$tmp_dir"
fi

# Remove old configs
print_status "Removing old configs..."
rm -rf "/home/$USER/.config/hypr" 2>/dev/null
rm -rf "/home/$USER/.config/kitty" 2>/dev/null
sudo rm -f /etc/sddm.conf 2>/dev/null
sudo rm -f /etc/default/grub 2>/dev/null

# Create symlinks
print_status "Creating symlinks..."
symlinks=(
    "fastfetch"
    "hypr"
    "kitty"
    "nvim"
    "rofi"
    "xdg-desktop-portal"
    "pywal"
    "wal"
    "scripts"
    "waybar"
    "qt5ct"
    "qt6ct"
    "kvantum"
)

for link in "${symlinks[@]}"; do
    source="/home/$USER/dots/$link"
    dest="/home/$USER/.config/$link"
    
    if directory_exists "$source"; then
        mkdir -p "/home/$USER/.config"
        if [ -e "$dest" ]; then
            rm -rf "$dest"
        fi
        if ln -sf "$source" "$dest"; then
            print_success "Symlink created for $link"
        else
            print_error "Failed to create symlink for $link"
        fi
    else
        print_warning "Source directory not found: $source"
    fi
done

# Create additional symlinks
additional_links=(
    "wallapers:/home/$USER/wallapers"
    ".icons:/home/$USER/.icons"
    ".themes:/home/$USER/.themes"
)

for link_pair in "${additional_links[@]}"; do
    IFS=':' read -r source_rel dest_path <<< "$link_pair"
    source="/home/$USER/dots/$source_rel"
    
    if directory_exists "$source"; then
        if [ -e "$dest_path" ]; then
            rm -rf "$dest_path"
        fi
        if ln -sf "$source" "$dest_path"; then
            print_success "Symlink created for $source_rel"
        else
            print_error "Failed to create symlink for $source_rel"
        fi
    else
        print_warning "Source directory not found: $source"
    fi
done

# System Wide Configs
print_status "Configuring system settings..."

# Cursor themes
if directory_exists "/home/$USER/dots/sys/cursors"; then
    sudo mkdir -p /usr/share/icons/
    sudo cp -r "/home/$USER/dots/sys/cursors/default" "/usr/share/icons/" 2>/dev/null
    sudo cp -r "/home/$USER/dots/sys/cursors/oreo_white_cursors" "/usr/share/icons/" 2>/dev/null
fi

# Load Theme (GNOME settings)
if command_exists gsettings; then
    print_status "Applying GNOME theme settings..."
    gsettings set org.gnome.desktop.interface cursor-theme "oreo_white_cursors" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface icon-theme "oomox-Tokyo-Night" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface gtk-theme "oomox-Tokyo-Night" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface font-name "MesloLGL Nerd Font 12" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface document-font-name "MesloLGL Nerd Font 12" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface monospace-font-name "MesloLGL Mono Nerd Font 12" 2>/dev/null || true
    gsettings set org.gnome.desktop.wm.preferences titlebar-font "MesloLGL Mono Nerd Font 12" 2>/dev/null || true
fi

# Load Waybar
waybar_script="/home/$USER/.config/scripts/waybar.sh"
if file_exists "$waybar_script"; then
    print_status "Starting Waybar..."
    bash "$waybar_script" 2>/dev/null &
fi

# Wallpaper and Pywal
print_status "Setting up wallpaper and colors..."
if command_exists swww-daemon; then
    swww-daemon 2>/dev/null &
    sleep 1
fi

swww_script="/home/$USER/.config/scripts/swww.sh"
if file_exists "$swww_script"; then
    bash "$swww_script" 2>/dev/null &
fi

# SDDM Theme
if directory_exists "/home/$USER/dots/sys/sddm"; then
    print_status "Configuring SDDM..."
    sudo mkdir -p /etc/
    sudo mkdir -p /usr/share/sddm/themes/
    sudo cp -f "/home/$USER/dots/sys/sddm/sddm.conf" "/etc/" 2>/dev/null
    sudo cp -rf "/home/$USER/dots/sys/sddm/tokyo-night/" "/usr/share/sddm/themes/" 2>/dev/null
fi

# Kvantum Theme
print_status "Configuring Kvantum..."
mkdir -p "/home/$USER/.config/Kvantum/pywal"
if file_exists "/home/$USER/.cache/wal/pywal.kvconfig"; then
    cp "/home/$USER/.cache/wal/pywal.kvconfig" "/home/$USER/.config/Kvantum/pywal/" 2>/dev/null
fi
if file_exists "/home/$USER/.cache/wal/pywal.svg"; then
    cp "/home/$USER/.cache/wal/pywal.svg" "/home/$USER/.config/Kvantum/pywal/" 2>/dev/null
fi

# GRUB Theme
if directory_exists "/home/$USER/dots/sys/grub"; then
    print_status "Configuring GRUB..."
    sudo mkdir -p /etc/default/
    sudo mkdir -p /usr/share/grub/themes/
    sudo cp -f "/home/$USER/dots/sys/grub/grub" "/etc/default/grub" 2>/dev/null
    sudo cp -rf "/home/$USER/dots/sys/grub/Matrices-circle-window" "/usr/share/grub/themes/" 2>/dev/null
    
    if command_exists grub-mkconfig; then
        sudo grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null
    fi
fi

# Clean up
print_status "Final cleanup..."
rm -rf "/home/$USER/dots/tmp/" 2>/dev/null

# Notification
if command_exists notify-send; then
    notify-send "Installation Complete" "Please Reboot Your PC"
fi

print_success "Installation completed!"

# Reboot prompt
if confirm_action "Do you want to reboot now?"; then
    print_status "Rebooting system in 5 seconds..."
    sleep 5
    sudo systemctl reboot
else
    print_status "Reboot cancelled. Please reboot manually later."
fi
