#!/bin/bash

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function for reboot confirmation
confirm_reboot() {
    local message="${1:-Do you want to reboot now?}"
    
    echo "========================================"
    print_warning "$message"
    echo "========================================"
    echo "1) Yes, reboot now"
    echo "2) No, don't reboot"
    echo "3) Reboot in 1 minute"
    echo "========================================"
    
    while true; do
        read -p "Select option (1-3): " choice
        
        case $choice in
            1)
                print_message "Rebooting immediately..."
                sudo reboot
                break
                ;;
            2)
                print_message "Reboot cancelled."
                break
                ;;
            3)
                print_message "System will reboot in 1 minute..."
                sudo shutdown -r +1 "System reboot initiated by script"
                break
                ;;
            *)
                print_error "Invalid option. Please enter 1, 2, or 3."
                ;;
        esac
    done
}

# Usage
echo "Setup completed successfully!"
confirm_reboot "Reboot is required for changes to take effect."
