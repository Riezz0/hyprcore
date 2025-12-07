#!/bin/bash

# Function to check if a package is installed
is_package_installed() {
    if command -v yay &>/dev/null; then
        yay -Qi "$1" &>/dev/null
    else
        pacman -Qi "$1" &>/dev/null
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

# Yay Installation (only if not already installed)
if ! command_exists yay; then
    echo "Installing yay..."
    sudo pacman -S --needed git base-devel && git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si
    cd .. || exit
else
    echo "yay is already installed, skipping..."
fi

# Package Installation with checks
packages=(
    swww qt5-quickcontrols qt5-quickcontrols2 qt5-graphicaleffects
    hypridle hyprlock hyprpicker tree qt5ct qt6ct qt5-styleplugins
    wl-clipboard firefox code neemo vlc nwg-look gnome-disk-utility
    nwg-displays zsh ttf-meslo-nerd ttf-font-awesome ttf-font-awesome-4
    ttf-font-awesome-5 waybar rust cargo fastfetch cmatrix pavucontrol
    net-tools waybar-module-pacman-updates-git python-pip python-psutil
    python-virtualenv python-requests python-hijri-converter python-pytz
    python-gobject xfce4-settings xfce-polkit exa libreoffice-fresh
    rofi-wayland neovim goverlay-git flatpak python-pywal16 python-pywalfox
    make linux-firmware dkms automake linux-zen-headers kvantum-qt5 
    chromium
)

to_install=()
for pkg in "${packages[@]}"; do
    if ! is_package_installed "$pkg"; then
        to_install+=("$pkg")
    else
        echo "Package $pkg is already installed, skipping..."
    fi
done

if [ ${#to_install[@]} -gt 0 ]; then
    echo "Installing packages: ${to_install[*]}"
    yay -S --needed --noconfirm "${to_install[@]}"
else
    echo "All packages are already installed."
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
    echo "Installing Oh My Zsh..."
    RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
else
    echo "Oh My Zsh is already installed, skipping..."
fi

# Clone and install plugins
for plugin in "${ohmyzsh_plugins[@]}"; do
    IFS='|' read -r plugin_name repo_url <<< "$plugin"
    plugin_tmp_dir="$tmp_dir/$plugin_name"
    plugin_dest_dir="/home/$USER/.oh-my-zsh/custom/plugins/$plugin_name"
    
    if ! directory_exists "$plugin_dest_dir"; then
        echo "Installing plugin: $plugin_name"
        if directory_exists "$plugin_tmp_dir"; then
            echo "Removing existing temporary directory: $plugin_tmp_dir"
            rm -rf "$plugin_tmp_dir"
        fi
        git clone --depth 1 "$repo_url" "$plugin_tmp_dir"
        
        if directory_exists "$plugin_tmp_dir"; then
            mkdir -p "/home/$USER/.oh-my-zsh/custom/plugins/"
            cp -r "$plugin_tmp_dir" "/home/$USER/.oh-my-zsh/custom/plugins/"
            echo "Successfully installed $plugin_name"
        else
            echo "Failed to clone $plugin_name"
        fi
    else
        echo "Plugin $plugin_name is already installed, skipping..."
    fi
done

# Change shell to zsh if not already
if [ "$SHELL" != "$(which zsh)" ]; then
    echo "Changing shell to zsh..."
    chsh -s "$(which zsh)"
else
    echo "zsh is already the default shell, skipping..."
fi

# Create symlink for .zshrc if it doesn't exist
zshrc_source="/home/$USER/dots/.zshrc"
zshrc_dest="/home/$USER/.zshrc"

if [ ! -L "$zshrc_dest" ] || [ ! -f "$zshrc_dest" ]; then
    echo "Creating .zshrc symlink..."
    if [ -f "$zshrc_dest" ]; then
        rm -f "$zshrc_dest"
    fi
    ln -sf "$zshrc_source" "$zshrc_dest"
else
    echo ".zshrc already exists, skipping..."
fi

# Clean up temporary directory
if directory_exists "$tmp_dir"; then
    echo "Cleaning up temporary directory..."
    rm -rf "$tmp_dir"
fi

echo "Installation completed!"
