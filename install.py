import gi
import subprocess
import threading
import os
import sys

# Configure PyGObject to use GTK 4
try:
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GLib
except ValueError:
    print("Error: Could not find GTK 4.0. Please ensure the 'gtk4' package is installed.")
    sys.exit(1)

# --- Configuration & Global Variables ---
USER = os.getenv('USER')
HOME = os.getenv('HOME')
DOTFILES_DIR = os.path.join(HOME, 'dots')
POLKIT_COMMAND = ['pkexec'] # pkexec will use the installed policy agent (like xfce-polkit)

# --- Utility Functions ---

def run_command_with_polkit(command_parts, description, callback):
    """Runs a command with elevated privileges using pkexec."""
    full_command = POLKIT_COMMAND + command_parts
    print(f"Running elevated command: {' '.join(full_command)}")
    GLib.timeout_add(10, callback, f"Attempting to run: {description} (Requires password)")
    return run_command_async(full_command, callback)

def run_command_async(command_parts, callback, cwd=None):
    """
    Runs a command asynchronously in a separate thread.
    Callback is a function that accepts one argument (the output/status string).
    """
    def target():
        try:
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=cwd
            )

            # Read output line-by-line in real-time
            for line in process.stdout:
                GLib.idle_add(callback, line.strip())

            process.wait()

            if process.returncode == 0:
                GLib.idle_add(callback, f"✅ Command successful: {' '.join(command_parts)}")
            else:
                GLib.idle_add(callback, f"❌ Command failed with exit code {process.returncode}: {' '.join(command_parts)}")
                
        except Exception as e:
            GLib.idle_add(callback, f"Critical Error running command: {e}")

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    return thread

# --- Installation Steps (Mapped from install.sh) ---

INSTALLATION_STEPS = [
    # 1. Install yay
    {
        "name": "Install & Update yay and Dependencies",
        "commands": [
            (['bash', '-c', f'if ! command -v yay &> /dev/null; then echo "Installing yay..."; {POLKIT_COMMAND[0]} pacman -S --needed --noconfirm git base-devel && git clone https://aur.archlinux.org/yay.git /tmp/yay && cd /tmp/yay && makepkg -si --noconfirm && cd ~ && echo "yay installed"; else echo "yay already installed"; fi'], 'Installing yay'),
            (['yay', '-Syyu'], 'System Update and Sync'),
        ],
        "requires_sudo": True # Handled by the bash command structure
    },
    # 2. Install Main Packages
    {
        "name": "Install Main Package List",
        "commands": [
            (['yay', '-S', '--needed', '--noconfirm', 
              'swww', 'qt5-quickcontrols', 'qt5-quickcontrols2', 'qt5-graphicaleffects', 
              'hypridle', 'hyprlock', 'hyprpicker', 'tree', 'qt5ct', 'qt6ct', 'qt5-styleplugins', 
              'wl-clipboard', 'firefox', 'code', 'nemo', 'vlc', 'nwg-look', 'gnome-disk-utility', 
              'nwg-displays', 'zsh', 'ttf-meslo-nerd', 'ttf-font-awesome', 'ttf-font-awesome-4', 
              'ttf-font-awesome-5', 'waybar', 'rust', 'cargo', 'fastfetch', 'cmatrix', 'pavucontrol', 
              'net-tools', 'python-pip', 'python-psutil', 'python-virtualenv', 'python-requests', 
              'python-hijri-converter', 'python-pytz', 'python-gobject', 'xfce4-settings', 
              'xfce-polkit', 'exa', 'libreoffice-fresh', 'rofi-wayland', 'neovim', 'goverlay-git', 
              'flatpak', 'python-pywal16', 'python-pywalfox', 'make', 'linux-firmware', 'dkms', 
              'automake', 'linux-zen-headers', 'kvantum-qt5', 'chromium', 'nemo-fileroller', 
              'waybar-module-pacman-updates-git', 'coolercontrol-bin', 'steam', 'lutris', 
              'python-geocoder'], 
             'Installing all necessary packages via yay'),
        ],
        "requires_sudo": False # yay handles privilege
    },
    # 3. Setup Directories & Fonts
    {
        "name": "Setup Directories and Fonts",
        "commands": [
            (['mkdir', '-p', f'{HOME}/git', f'{HOME}/venv', f'{HOME}/tmp/'], 'Creating user directories'),
            (['mkdir', '-p', f'{HOME}/.local/share/fonts'], 'Creating fonts directory'),
            (['cp', '-r', f'{DOTFILES_DIR}/fonts/.', f'{HOME}/.local/share/fonts'], 'Copying fonts'),
            (['fc-cache', '-fv'], 'Updating font cache'),
        ],
        "requires_sudo": False
    },
    # 4. Install Flatpaks
    {
        "name": "Install Flatpak Applications",
        "commands": [
            (['flatpak', 'install', '--noninteractive', 'flathub', 'org.localsend.localsend_app'], 'Installing Localsend'),
            (['flatpak', 'install', '--noninteractive', 'flathub', 'com.github.tchx84.Flatseal'], 'Installing Flatseal'),
            (['flatpak', 'install', '--noninteractive', 'flathub', 'com.usebottles.bottles'], 'Installing Bottles'),
            (['flatpak', 'install', '--noninteractive', 'flathub', 'net.lutris.Lutris'], 'Installing Lutris'),
            (['flatpak', 'install', '--noninteractive', 'flathub', 'net.rpcs3.RPCS3'], 'Installing RPCS3'),
        ],
        "requires_sudo": False
    },
    # 5. Zsh Setup
    {
        "name": "Configure Zsh and Plugins",
        "commands": [
            (['git', 'clone', 'https://github.com/zsh-users/zsh-autosuggestions.git', f'{DOTFILES_DIR}/tmp/zsh-autosuggestions/'], 'Cloning zsh-autosuggestions'),
            (['git', 'clone', 'https://github.com/zsh-users/zsh-syntax-highlighting.git', f'{DOTFILES_DIR}/tmp/zsh-syntax-highlighting/'], 'Cloning zsh-syntax-highlighting'),
            (['git', 'clone', 'https://github.com/zdharma-continuum/fast-syntax-highlighting.git', f'{DOTFILES_DIR}/tmp/fast-syntax-highlighting/'], 'Cloning fast-syntax-highlighting'),
            (['git', 'clone', '--depth', '1', 'https://github.com/marlonrichert/zsh-autocomplete.git', f'{DOTFILES_DIR}/tmp/zsh-autocomplete/'], 'Cloning zsh-autocomplete'),
            (['git', 'clone', 'https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git', f'{DOTFILES_DIR}/tmp/autoswitch_virtualenv/'], 'Cloning zsh-autoswitch-virtualenv'),
            (['bash', '-c', f'RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended'], 'Installing Oh My Zsh'),
            (['chsh', '-s', '/usr/bin/zsh'], 'Setting Zsh as default shell'),
            (['mkdir', '-p', f'{HOME}/.oh-my-zsh/custom/plugins'], 'Creating OMZ plugins directory'),
            (['cp', '-r', f'{DOTFILES_DIR}/tmp/autoswitch_virtualenv/', f'{HOME}/.oh-my-zsh/custom/plugins/'], 'Copying autoswitch_virtualenv'),
            (['cp', '-r', f'{DOTFILES_DIR}/tmp/fast-syntax-highlighting/', f'{HOME}/.oh-my-zsh/custom/plugins/'], 'Copying fast-syntax-highlighting'),
            (['cp', '-r', f'{DOTFILES_DIR}/tmp/zsh-autocomplete/', f'{HOME}/.oh-my-zsh/custom/plugins/'], 'Copying zsh-autocomplete'),
            (['cp', '-r', f'{DOTFILES_DIR}/tmp/zsh-autosuggestions/', f'{HOME}/.oh-my-zsh/custom/plugins/'], 'Copying zsh-autosuggestions'),
            (['cp', '-r', f'{DOTFILES_DIR}/tmp/zsh-syntax-highlighting/', f'{HOME}/.oh-my-zsh/custom/plugins/'], 'Copying zsh-syntax-highlighting'),
        ],
        "requires_sudo": False
    },
    # 6. Clean and Symlink Dotfiles
    {
        "name": "Clean and Symlink Dotfiles",
        "commands": [
            (['rm', '-rf', f'{DOTFILES_DIR}/tmp/'], 'Cleaning up Zsh plugin clones'),
            (['rm', '-rf', f'{HOME}/.config/hypr'], 'Cleaning old hypr config'),
            (['rm', '-rf', f'{HOME}/.config/kitty'], 'Cleaning old kitty config'),
            (['rm', f'{HOME}/.zshrc'], 'Cleaning old .zshrc'),
            (['ln', '-s', f'{DOTFILES_DIR}/.zshrc', f'{HOME}/'], 'Symlinking .zshrc'),
            (['ln', '-s', f'{DOTFILES_DIR}/fastfetch/', f'{HOME}/.config/'], 'Symlinking fastfetch config'),
            (['ln', '-s', f'{DOTFILES_DIR}/hypr/', f'{HOME}/.config/'], 'Symlinking hypr config'),
            (['ln', '-s', f'{DOTFILES_DIR}/kitty', f'{HOME}/.config/'], 'Symlinking kitty config'),
            (['ln', '-s', f'{DOTFILES_DIR}/Kvantum/', f'{HOME}/.config/'], 'Symlinking Kvantum config'),
            (['ln', '-s', f'{DOTFILES_DIR}/nvim/', f'{HOME}/.config/'], 'Symlinking nvim config'),
            (['ln', '-s', f'{DOTFILES_DIR}/pywal/', f'{HOME}/.config/'], 'Symlinking pywal config'),
            (['ln', '-s', f'{DOTFILES_DIR}/qt5ct/', f'{HOME}/.config/'], 'Symlinking qt5ct config'),
            (['ln', '-s', f'{DOTFILES_DIR}/qt6ct/', f'{HOME}/.config/'], 'Symlinking qt6ct config'),
            (['ln', '-s', f'{DOTFILES_DIR}/rofi/', f'{HOME}/.config/'], 'Symlinking rofi config'),
            (['ln', '-s', f'{DOTFILES_DIR}/scripts/', f'{HOME}/.config/'], 'Symlinking scripts config'),
            (['ln', '-s', f'{DOTFILES_DIR}/wal/', f'{HOME}/.config/'], 'Symlinking wal config'),
            (['ln', '-s', f'{DOTFILES_DIR}/wallpapers/', f'{HOME}/.config/'], 'Symlinking wallpapers config'),
            (['ln', '-s', f'{DOTFILES_DIR}/waybar/', f'{HOME}/.config/'], 'Symlinking waybar config'),
            (['ln', '-s', f'{DOTFILES_DIR}/xdg-desktop-portal/', f'{HOME}/.config/'], 'Symlinking xdg-desktop-portal config'),
            (['ln', '-s', f'{DOTFILES_DIR}/.icons/', f'{HOME}/'], 'Symlinking .icons'),
            (['ln', '-s', f'{DOTFILES_DIR}/.themes/', f'{HOME}/'], 'Symlinking .themes'),
            (['rm', f'{HOME}/.config/hypr/monitors.conf'], 'Removing monitors.conf (to be created by nwg-displays)'),
        ],
        "requires_sudo": True # Only to clean sddm.conf and grub, which are now handled in later steps
    },
    # 7. GTK/GNOME Settings and Wallpaper
    {
        "name": "Apply GTK/GNOME Settings and Wallpaper",
        "commands": [
            (['gsettings', 'set', 'org.gnome.desktop.interface', 'cursor-theme', 'oreo_white_cursors'], 'Setting cursor theme'),
            (['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', 'oomox-Tokyo-Night'], 'Setting icon theme'),
            (['gsettings', 'set', 'org.gnome.desktop.interface', 'gtk-theme', 'oomox-Tokyo-Night'], 'Setting GTK theme'),
            (['gsettings', 'set', 'org.gnome.desktop.interface', 'font-name', 'MesloLGL Nerd Font 12'], 'Setting interface font'),
            (['gsettings', 'set', 'org.gnome.desktop.interface', 'document-font-name', 'MesloLGL Nerd Font 12'], 'Setting document font'),
            (['gsettings', 'set', 'org.gnome.desktop.interface', 'monospace-font-name', 'MesloLGL Mono Nerd Font 12'], 'Setting monospace font'),
            (['gsettings', 'set', 'org.gnome.desktop.wm.preferences', 'titlebar-font', 'MesloLGL Mono Nerd Font 12'], 'Setting titlebar font'),
            (['bash', '-c', 'swww-daemon 2>/dev/null &'], 'Starting swww daemon'),
            (['bash', f'{HOME}/scripts/swww.sh'], 'Applying initial wallpaper'),
            (['wal', '--theme', f'{HOME}/.config/pywal/themes/active.json'], 'Applying pywal colors'),
            (['cp', f'{HOME}/.cache/wal/pywal.kvconfig', f'{HOME}/.config/Kvantum/pywal/pywal.kvconfig'], 'Copying Kvantum config'),
            (['cp', f'{HOME}/.cache/wal/pywal.svg', f'{HOME}/.config/Kvantum/pywal/pywal.svg'], 'Copying Kvantum SVG'),
        ],
        "requires_sudo": False
    },
    # 8. SDDM/GRUB Setup (Requires Sudo)
    {
        "name": "Configure SDDM and GRUB Themes",
        "commands": [
            (['rm', '/etc/sddm.conf'], 'Removing old sddm.conf'),
            (['rm', '/etc/default/grub'], 'Removing old grub config'),
            (['rm', '-rf', '/usr/share/icons/default'], 'Removing default cursor symlink'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/cursors/default', '/usr/share/icons/'], 'Copying new default cursor theme'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/cursors/oreo_white_cursors', '/usr/share/icons/'], 'Copying oreo_white_cursors theme'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/sddm/sddm.conf', '/etc/'], 'Copying sddm.conf'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/sddm/tokyo-night/', '/usr/share/sddm/themes/'], 'Copying SDDM Tokyo Night theme'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/grub/grub', '/etc/default/'], 'Copying new GRUB config'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/grub/tokyo-night', '/usr/share/grub/themes/'], 'Copying GRUB Tokyo Night theme'),
            (['grub-mkconfig', '-o', '/boot/grub/grub.cfg'], 'Updating GRUB configuration'),
        ],
        "requires_sudo": True
    },
    # 9. Custom Kernel Module (nct6687d)
    {
        "name": "Install nct6687d Kernel Module",
        "commands": [
            (['git', 'clone', 'https://github.com/Fred78290/nct6687d', f'{HOME}/tmp/nct6687d'], 'Cloning nct6687d repository'),
            (['make', 'dkms/install'], 'Installing dkms module', f'{HOME}/tmp/nct6687d'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/no_nct6683.conf', '/etc/modprobe.d/'], 'Copying no_nct6683.conf'),
            (['mkdir', '-p', '/etc/modules-load.d/'], 'Creating modules-load.d directory'),
            (['cp', '-r', f'{DOTFILES_DIR}/sys/nct6687.conf', '/etc/modules-load.d/nct6687.conf'], 'Copying nct6687 load config'),
            (['modprobe', 'nct6687'], 'Loading nct6687 module'),
        ],
        "requires_sudo": True
    },
    # 10. nwg-displays (Interactive Step)
    {
        "name": "Monitor Configuration (Manual Step)",
        "commands": [
            (['echo', 'Launching nwg-displays... Please close the window when done.'], 'Interactive step guidance'),
            (['nwg-displays'], 'Launching nwg-displays for configuration'),
        ],
        "requires_sudo": False,
        "interactive": True
    },
]

# --- GTK Application Class ---

class DotfilesInstaller(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.yourdomain.DotfilesInstaller",
                         flags=gi.repository.Gio.ApplicationFlags.FLAGS_NONE)
        self.current_step_index = 0
        self.current_command_index = 0
        self.active_thread = None

    def do_activate(self):
        # Create the main window
        self.window = Gtk.ApplicationWindow(application=self, title="Dotfiles Installer")
        self.window.set_default_size(800, 600)
        
        # Main Box (Vertical)
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_vbox.set_margin_start(12)
        main_vbox.set_margin_end(12)
        main_vbox.set_margin_top(12)
        main_vbox.set_margin_bottom(12)

        # Title Label
        title_label = Gtk.Label(label="🚀 Dotfiles Installation Manager ⚙️")
        title_label.add_css_class('title-1')
        main_vbox.append(title_label)
        
        # Step Label (Current Step)
        self.step_label = Gtk.Label(label="Initializing...")
        main_vbox.append(self.step_label)

        # Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Waiting to start...")
        self.progress_bar.set_show_text(True)
        main_vbox.append(self.progress_bar)

        # Output/Log View (Scrolled Window + Text View)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.text_buffer = self.log_view.get_buffer()
        scrolled_window.set_child(self.log_view)
        main_vbox.append(scrolled_window)

        # Button Box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.start_button = Gtk.Button(label="Start Installation")
        self.start_button.connect("clicked", self.on_start_clicked)
        button_box.append(self.start_button)
        
        self.reboot_button = Gtk.Button(label="Finish & Reboot")
        self.reboot_button.connect("clicked", self.on_reboot_clicked)
        self.reboot_button.set_sensitive(False)
        button_box.append(self.reboot_button)
        
        main_vbox.append(button_box)

        self.window.set_child(main_vbox)
        self.window.present()

    def update_log(self, message):
        """Appends a message to the text view and scrolls to the end."""
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, message + "\n")
        # Scroll to the end
        adj = self.log_view.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def update_progress(self, current_total_command_index):
        """Updates the progress bar based on the current command index."""
        total_commands = sum(len(step['commands']) for step in INSTALLATION_STEPS)
        fraction = current_total_command_index / total_commands
        self.progress_bar.set_fraction(fraction)
        
        step = INSTALLATION_STEPS[self.current_step_index]
        text = f"Step {self.current_step_index + 1}/{len(INSTALLATION_STEPS)}: {step['name']} ({self.current_command_index+1}/{len(step['commands'])})"
        self.progress_bar.set_text(text)

    def on_start_clicked(self, button):
        """Start the installation process."""
        button.set_sensitive(False)
        self.start_next_step()

    def start_next_step(self):
        """Initiates the next installation step or finishes."""
        if self.current_step_index >= len(INSTALLATION_STEPS):
            self.update_log("=========================================")
            self.update_log("🎉 **Installation Complete!**")
            self.update_log("All steps finished. You can now press 'Finish & Reboot'.")
            self.update_log("=========================================")
            self.reboot_button.set_sensitive(True)
            return

        step = INSTALLATION_STEPS[self.current_step_index]
        self.update_log(f"\n--- Starting Step: {step['name']} ---")
        self.current_command_index = 0
        
        if step.get('interactive', False):
            # Handle the nwg-displays interactive step
            self.update_log(f"*** INTERACTIVE STEP: {step['name']} ***")
            self.update_log("Please wait for the application to launch. Close it to continue.")
            
            # Run the interactive command and wait for it
            command_parts, description = step['commands'][1] # Assumes nwg-displays is the second command
            
            def interactive_callback(output):
                """A modified callback that also checks for the return of the interactive command."""
                self.update_log(output)
                if output.startswith("✅ Command successful") or output.startswith("❌ Command failed"):
                    # The nwg-displays process has finished
                    self.update_log("✅ Interactive step finished. Continuing...")
                    GLib.idle_add(self.advance_to_next_step)

            run_command_async(command_parts, interactive_callback)
            
        else:
            self.run_next_command()


    def run_next_command(self):
        """Runs the next command within the current step."""
        step = INSTALLATION_STEPS[self.current_step_index]
        
        if self.current_command_index >= len(step['commands']):
            self.update_log(f"--- Step '{step['name']}' finished. ---")
            self.advance_to_next_step()
            return

        command_tuple = step['commands'][self.current_command_index]
        command_parts, description = command_tuple[0], command_tuple[1]
        
        # Check if a custom working directory is specified (for 'make dkms/install')
        cwd = command_tuple[2] if len(command_tuple) > 2 else None
        
        # Calculate the overall command index for progress bar
        current_total_command_index = sum(len(INSTALLATION_STEPS[i]['commands']) for i in range(self.current_step_index)) + self.current_command_index
        self.update_progress(current_total_command_index)

        def command_callback(output):
            """Callback for command output, drives the next command execution."""
            self.update_log(output)
            
            # Check for command completion status markers
            if output.startswith("✅ Command successful") or output.startswith("❌ Command failed"):
                self.current_command_index += 1
                GLib.idle_add(self.run_next_command)

        if step.get('requires_sudo', False):
            self.active_thread = run_command_with_polkit(command_parts, description, command_callback)
        elif command_parts[0] == 'yay':
            # yay handles its own sudo via policy, so treat it as non-polkit for simplicity
            self.active_thread = run_command_async(command_parts, command_callback, cwd=cwd)
        elif command_parts[0] == 'chsh':
             # chsh requires polkit in most cases to change the shell
             self.active_thread = run_command_with_polkit(command_parts, description, command_callback)
        else:
            self.active_thread = run_command_async(command_parts, command_callback, cwd=cwd)

    def advance_to_next_step(self):
        """Moves the installation to the next logical step."""
        self.current_step_index += 1
        self.current_command_index = 0
        self.start_next_step()

    def on_reboot_clicked(self, button):
        """Runs the final reboot script using pkexec."""
        self.update_log("\n*** Launching final reboot script and shutting down the installer. ***")
        
        def reboot_callback(output):
            self.update_log(output)
            if output.startswith("✅ Command successful"):
                self.update_log("Reboot command executed. System should restart soon.")
            
        run_command_with_polkit(['bash', f'{DOTFILES_DIR}/reboot.sh'], 'Running final reboot script', reboot_callback)
        
        # Give a moment for the reboot script to launch, then quit
        GLib.timeout_add_seconds(3, self.quit)
        
# --- Main Execution ---

if __name__ == "__main__":
    # Ensure dotfiles directory exists and contains the files
    if not os.path.isdir(DOTFILES_DIR):
        print(f"Error: Dotfiles directory not found at {DOTFILES_DIR}")
        print("Please clone your dotfiles repo to ~/dots before running the installer.")
        sys.exit(1)

    app = DotfilesInstaller()
    sys.exit(app.run(sys.argv))
