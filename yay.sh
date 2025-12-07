#!/bin/bash

# Script to check and install yay if not present

# Check if running as normal user (yay should not be installed as root)
if [ "$EUID" -eq 0 ]; then
    echo "Please run this script as a normal user, not as root."
    exit 1
fi

# Function to check if yay is installed
check_yay_installed() {
    if command -v yay &> /dev/null; then
        return 0  # yay is installed
    else
        return 1  # yay is not installed
    fi
}

# Function to install yay
install_yay() {
    echo "yay is not installed. Installing yay..."
    
    # Create temporary directory for yay installation
    temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Clone yay repository
    echo "Cloning yay repository..."
    git clone https://aur.archlinux.org/yay.git
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to clone yay repository"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    cd yay
    
    # Build and install yay
    echo "Building yay..."
    makepkg -si --noconfirm
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to build or install yay"
        cd /
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Clean up
    cd /
    rm -rf "$temp_dir"
    
    echo "yay installation completed successfully!"
}

# Main execution
echo "Checking if yay is installed..."

if check_yay_installed; then
    echo "yay is already installed."
    echo "Version: $(yay --version | head -n 1)"
else
    echo "yay not found. Proceeding with installation..."
    
    # Check if git is installed (required for yay installation)
    if ! command -v git &> /dev/null; then
        echo "Error: git is not installed. Please install git first:"
        echo "sudo pacman -S git"
        exit 1
    fi
    
    # Check if base-devel is installed
    if ! pacman -Qg base-devel &> /dev/null; then
        echo "Warning: base-devel package group is not installed."
        echo "It's recommended to install it for building AUR packages:"
        echo "sudo pacman -S --needed base-devel"
        read -p "Do you want to install base-devel now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo pacman -S --needed base-devel
        fi
    fi
    
    install_yay
fi

# Verify installation
if check_yay_installed; then
    echo "✓ yay is ready to use!"
else
    echo "✗ Something went wrong. yay is not installed."
    exit 1
fi
