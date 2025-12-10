#!/usr/bin/env python3
"""
PyGObject Dotfiles Installer - GUI Version
All installation happens within the app with live output display.
"""

import os
import sys
import shutil
import subprocess
import json
import threading
import time
import queue
from pathlib import Path
from enum import Enum
import signal
import select
import fcntl
import termios

# GTK imports
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, GLib, Gio, Pango, Vte, Gdk


class InstallStep(Enum):
    """Installation steps enumeration"""
    PREPARE = "Preparing"
    YAY = "Installing YAY"
    PACKAGES = "Installing Packages"
    DIRECTORIES = "Creating Directories"
    FONTS = "Installing Fonts"
    ZSH_PLUGINS = "Cloning ZSH Plugins"
    ZSH_SETUP = "Setting up ZSH"
    SYMLINKS = "Creating Symlinks"
    SYSTEM_FILES = "Copying System Files"
    GSETTINGS = "Configuring GNOME"
    KERNEL_MODULE = "Setting up Kernel Module"
    NWG_DISPLAYS = "Display Configuration"
    CLEANUP = "Cleaning up"
    COMPLETE = "Complete"


class DotfileInstaller:
    """Main installer class with GUI integration"""
    
    def __init__(self, dotfiles_path=None, gui_callback=None):
        self.dotfiles_path = dotfiles_path or Path.home() / "dots"
        self.user = os.getenv("USER")
        self.home = Path.home()
        self.log_file = self.home / ".dotfiles-install.log"
        self.config = self.load_config()
        self.gui_callback = gui_callback
        self.current_step = InstallStep.PREPARE
        self.progress = 0
        self.running = True
        self.output_queue = queue.Queue()
        self.process = None
        
    def load_config(self):
        """Load configuration from JSON file"""
        config_path = self.dotfiles_path / "installer-config.json"
        default_config = {
            "packages": {
                "yay_packages": [
                    "swww", "qt5-quickcontrols", "qt5-quickcontrols2", "qt5-graphicaleffects",
                    "hypridle", "hyprlock", "hyprpicker", "tree", "qt5ct", "qt6ct", "qt5-styleplugins",
                    "wl-clipboard", "firefox", "code", "nemo", "vlc", "nwg-look", "gnome-disk-utility",
                    "nwg-displays", "zsh", "ttf-meslo-nerd", "ttf-font-awesome", "ttf-font-awesome-4",
                    "ttf-font-awesome-5", "waybar", "rust", "cargo", "fastfetch", "cmatrix", "pavucontrol",
                    "net-tools", "python-pip", "python-psutil", "python-virtualenv", "python-requests",
                    "python-hijri-converter", "python-pytz", "python-gobject", "xfce4-settings",
                    "xfce-polkit", "exa", "libreoffice-fresh", "rofi-wayland", "neovim", "goverlay-git",
                    "flatpak", "python-pywal16", "python-pywalfox", "make", "linux-firmware", "dkms",
                    "automake", "linux-zen-headers", "kvantum-qt5", "chromium", "nemo-fileroller",
                    "waybar-module-pacman-updates-git", "coolercontrol-bin"
                ],
                "flatpak_apps": [
                    "org.localsend.localsend_app",
                    "com.github.tchx84.Flatseal",
                    "com.usebottles.bottles"
                ]
            },
            "repositories": {
                "zsh_plugins": [
                    {"url": "https://github.com/zsh-users/zsh-autosuggestions.git", "name": "zsh-autosuggestions"},
                    {"url": "https://github.com/zsh-users/zsh-syntax-highlighting.git", "name": "zsh-syntax-highlighting"},
                    {"url": "https://github.com/zdharma-continuum/fast-syntax-highlighting.git", "name": "fast-syntax-highlighting"},
                    {"url": "https://github.com/marlonrichert/zsh-autocomplete.git", "name": "zsh-autocomplete"},
                    {"url": "https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git", "name": "autoswitch_virtualenv"}
                ]
            },
            "symlinks": [
                ".zshrc",
                "fastfetch/",
                "hypr/",
                "kitty/",
                "Kvantum/",
                "nvim/",
                "pywal/",
                "qt5ct/",
                "qt6ct/",
                "rofi/",
                "scripts/",
                "wal/",
                "wallpapers/",
                "waybar/",
                "xdg-desktop-portal/",
                ".icons/",
                ".themes/"
            ]
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return {**default_config, **json.load(f)}
            except:
                return default_config
        return default_config
    
    def update_progress(self, step, progress, message=""):
        """Update progress for GUI"""
        self.current_step = step
        self.progress = progress
        if self.gui_callback:
            GLib.idle_add(self.gui_callback, step, progress, message)
    
    def log_output(self, text, is_error=False):
        """Send output to GUI"""
        if self.gui_callback:
            GLib.idle_add(self.gui_callback, "output", text, is_error)
    
    def run_command_with_output(self, cmd, step_name, step_weight=1):
        """Run shell command and capture output for GUI"""
        total_steps = 14  # Total number of installation steps
        step_value = 100 / total_steps
        
        self.log_output(f"\n🔧 {step_name}\n")
        self.log_output(f"$ {cmd}\n")
        
        try:
            # Create process with real-time output capture
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.process = process
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output:
                    self.log_output(output)
                if process.poll() is not None:
                    # Read any remaining output
                    remaining = process.stdout.read()
                    if remaining:
                        self.log_output(remaining)
                    break
                time.sleep(0.01)
            
            return_code = process.wait()
            self.process = None
            
            if return_code == 0:
                self.log_output(f"✓ {step_name} completed successfully\n")
                self.progress += step_value * step_weight
                self.update_progress(self.current_step, self.progress, f"{step_name} completed")
                return True
            else:
                self.log_output(f"✗ {step_name} failed with code {return_code}\n", True)
                return False
                
        except Exception as e:
            self.log_output(f"✗ Error in {step_name}: {str(e)}\n", True)
            return False
    
    def check_yay(self):
        """Check if yay is installed"""
        return subprocess.call("command -v yay", shell=True, 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL) == 0
    
    def install_yay(self):
        """Install yay AUR helper"""
        self.update_progress(InstallStep.YAY, 5, "Checking YAY installation")
        
        if not self.check_yay():
            self.log_output("YAY not found, installing...\n")
            
            # Install base-devel and git
            if not self.run_command_with_output(
                "sudo pacman -S --needed --noconfirm git base-devel",
                "Installing prerequisites"
            ):
                return False
            
            # Clone yay
            if not self.run_command_with_output(
                "git clone https://aur.archlinux.org/yay.git /tmp/yay",
                "Cloning YAY repository"
            ):
                return False
            
            # Build and install yay
            if not self.run_command_with_output(
                "cd /tmp/yay && makepkg -si --noconfirm",
                "Building and installing YAY"
            ):
                return False
            
            self.log_output("✓ YAY installed successfully\n")
        else:
            self.log_output("✓ YAY already installed\n")
        
        return True
    
    def install_packages(self):
        """Install packages using yay"""
        self.update_progress(InstallStep.PACKAGES, 15, "Updating package database")
        
        # Update package database
        if not self.run_command_with_output(
            "yay -Syyu",
            "Updating package database"
        ):
            return False
        
        # Install packages in batches to avoid command line too long
        packages = self.config["packages"]["yay_packages"]
        batch_size = 10
        
        for i in range(0, len(packages), batch_size):
            batch = packages[i:i + batch_size]
            progress_msg = f"Installing packages {i+1}-{min(i+batch_size, len(packages))} of {len(packages)}"
            
            self.update_progress(
                InstallStep.PACKAGES,
                20 + (i / len(packages)) * 30,
                progress_msg
            )
            
            if not self.run_command_with_output(
                f"yay -S --needed --noconfirm {' '.join(batch)}",
                f"Installing package batch"
            ):
                return False
        
        return True
    
    def setup_directories(self):
        """Create necessary directories"""
        self.update_progress(InstallStep.DIRECTORIES, 55, "Creating directories")
        
        directories = [
            self.home / "git",
            self.home / "venv",
            self.home / "tmp",
            self.home / ".local" / "share" / "fonts",
            self.home / ".oh-my-zsh" / "custom" / "plugins",
            self.dotfiles_path / "tmp"
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                self.log_output(f"Created directory: {directory}\n")
            except Exception as e:
                self.log_output(f"Error creating {directory}: {e}\n", True)
                return False
        
        # Create system directory with sudo
        if not self.run_command_with_output(
            "sudo mkdir -p /etc/modules-load.d/",
            "Creating system directories"
        ):
            return False
        
        return True
    
    def install_fonts(self):
        """Install custom fonts"""
        self.update_progress(InstallStep.FONTS, 60, "Installing fonts")
        
        fonts_src = self.dotfiles_path / "fonts"
        fonts_dst = self.home / ".local" / "share" / "fonts"
        
        if not fonts_src.exists():
            self.log_output("No fonts directory found, skipping...\n")
            return True
        
        try:
            # Copy fonts
            for font_file in fonts_src.glob("*"):
                if font_file.is_file():
                    shutil.copy2(font_file, fonts_dst)
                    self.log_output(f"Installed font: {font_file.name}\n")
            
            # Update font cache
            if not self.run_command_with_output(
                "fc-cache -fv",
                "Updating font cache"
            ):
                return False
            
            return True
        except Exception as e:
            self.log_output(f"Error installing fonts: {e}\n", True)
            return False
    
    def clone_zsh_plugins(self):
        """Clone ZSH plugins"""
        self.update_progress(InstallStep.ZSH_PLUGINS, 65, "Cloning ZSH plugins")
        
        tmp_dir = self.dotfiles_path / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        repos = self.config["repositories"]["zsh_plugins"]
        
        for i, repo_info in enumerate(repos):
            repo_url = repo_info["url"]
            repo_name = repo_info["name"]
            repo_path = tmp_dir / repo_name
            
            self.update_progress(
                InstallStep.ZSH_PLUGINS,
                65 + (i / len(repos)) * 5,
                f"Cloning {repo_name}"
            )
            
            if repo_name == "zsh-autocomplete":
                cmd = f"git clone --depth 1 -- {repo_url} {repo_path}"
            else:
                cmd = f"git clone {repo_url} {repo_path}"
            
            if not self.run_command_with_output(cmd, f"Cloning {repo_name}"):
                return False
        
        return True
    
    def setup_zsh(self):
        """Setup ZSH with Oh My Zsh"""
        self.update_progress(InstallStep.ZSH_SETUP, 72, "Setting up ZSH")
        
        # Install Oh My Zsh
        self.log_output("Installing Oh My Zsh...\n")
        if not self.run_command_with_output(
            'RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended',
            "Installing Oh My Zsh"
        ):
            return False
        
        # Change shell to ZSH
        zsh_path = shutil.which("zsh")
        if zsh_path:
            if not self.run_command_with_output(
                f"chsh -s {zsh_path}",
                "Setting ZSH as default shell"
            ):
                return False
        
        # Copy ZSH plugins
        tmp_dir = self.dotfiles_path / "tmp"
        plugins_dir = self.home / ".oh-my-zsh" / "custom" / "plugins"
        
        for plugin_dir in tmp_dir.iterdir():
            if plugin_dir.is_dir():
                try:
                    dst_dir = plugins_dir / plugin_dir.name
                    if dst_dir.exists():
                        shutil.rmtree(dst_dir)
                    shutil.copytree(plugin_dir, dst_dir)
                    self.log_output(f"Installed plugin: {plugin_dir.name}\n")
                except Exception as e:
                    self.log_output(f"Error copying plugin {plugin_dir.name}: {e}\n", True)
        
        return True
    
    def create_symlinks(self):
        """Create symbolic links for dotfiles"""
        self.update_progress(InstallStep.SYMLINKS, 78, "Creating symlinks")
        
        # Remove existing configs
        configs_to_remove = [
            self.home / ".config" / "hypr",
            self.home / ".config" / "kitty",
            self.home / ".zshrc"
        ]
        
        for config in configs_to_remove:
            if config.exists():
                try:
                    if config.is_symlink():
                        config.unlink()
                    else:
                        if config.is_dir():
                            shutil.rmtree(config)
                        else:
                            config.unlink()
                    self.log_output(f"Removed: {config}\n")
                except Exception as e:
                    self.log_output(f"Error removing {config}: {e}\n", True)
        
        # Create symlinks
        for i, link in enumerate(self.config["symlinks"]):
            src = self.dotfiles_path / link.strip('/')
            dst = self.home / link.strip('/')
            
            if not src.exists():
                self.log_output(f"Source not found: {src}, skipping...\n")
                continue
            
            try:
                # Ensure parent directory exists
                dst.parent.mkdir(parents=True, exist_ok=True)
                
                # Remove existing file/directory
                if dst.exists():
                    if dst.is_symlink():
                        dst.unlink()
                    else:
                        if dst.is_dir():
                            shutil.rmtree(dst)
                        else:
                            dst.unlink()
                
                # Create symlink
                dst.symlink_to(src, target_is_directory=src.is_dir())
                self.log_output(f"Linked: {src} -> {dst}\n")
                
            except Exception as e:
                self.log_output(f"Error linking {src}: {e}\n", True)
                return False
        
        return True
    
    def setup_system_files(self):
        """Copy system configuration files"""
        self.update_progress(InstallStep.SYSTEM_FILES, 82, "Setting up system files")
        
        # Setup will be done in the main installation function
        # This is a placeholder that will be implemented with specific commands
        return True
    
    def setup_gsettings(self):
        """Configure GNOME settings"""
        self.update_progress(InstallStep.GSETTINGS, 85, "Configuring GNOME settings")
        
        settings = [
            ("org.gnome.desktop.interface cursor-theme", "oreo_white_cursors"),
            ("org.gnome.desktop.interface icon-theme", "oomox-Tokyo-Night"),
            ("org.gnome.desktop.interface gtk-theme", "oomox-Tokyo-Night"),
            ("org.gnome.desktop.interface font-name", "MesloLGL Nerd Font 12"),
            ("org.gnome.desktop.interface document-font-name", "MesloLGL Nerd Font 12"),
            ("org.gnome.desktop.interface monospace-font-name", "MesloLGL Mono Nerd Font 12"),
            ("org.gnome.desktop.wm.preferences titlebar-font", "MesloLGL Mono Nerd Font 12")
        ]
        
        for key, value in settings:
            if not self.run_command_with_output(
                f'gsettings set {key} "{value}"',
                f"Setting {key.split('.')[-1]}"
            ):
                return False
        
        return True
    
    def setup_nct6687_module(self):
        """Setup NCT6687 kernel module"""
        self.update_progress(InstallStep.KERNEL_MODULE, 88, "Setting up kernel module")
        
        # Clone repository
        module_dir = self.home / "tmp" / "nct6687d"
        
        if not self.run_command_with_output(
            f"git clone https://github.com/Fred78290/nct6687d {module_dir}",
            "Cloning NCT6687 module"
        ):
            return False
        
        # Build and install
        if not self.run_command_with_output(
            f"cd {module_dir} && make dkms/install",
            "Building kernel module"
        ):
            return False
        
        # Copy config files
        sys_dir = self.dotfiles_path / "sys"
        if sys_dir.exists():
            if not self.run_command_with_output(
                f"sudo cp -r {sys_dir}/no_nct6683.conf /etc/modprobe.d/",
                "Copying module blacklist"
            ):
                return False
            
            if not self.run_command_with_output(
                f"sudo cp -r {sys_dir}/nct6687.conf /etc/modules-load.d/nct6687.conf",
                "Copying module config"
            ):
                return False
        
        # Load module
        if not self.run_command_with_output(
            "sudo modprobe nct6687",
            "Loading kernel module"
        ):
            return False
        
        return True
    
    def run_nwg_displays(self):
        """Run nwg-displays for monitor configuration"""
        self.update_progress(InstallStep.NWG_DISPLAYS, 92, "Display configuration")
        
        self.log_output("\n" + "="*60 + "\n")
        self.log_output("🚀 Launching nwg-displays for display configuration...\n")
        self.log_output("📺 Please set up your monitors in the nwg-displays window.\n")
        self.log_output("❌ Close the nwg-displays window when you're done.\n")
        self.log_output("="*60 + "\n\n")
        
        # Run nwg-displays
        process = subprocess.Popen("nwg-displays", shell=True)
        process.wait()
        
        self.log_output("✅ Display configuration saved!\n")
        return True
    
    def cleanup(self):
        """Clean up temporary files"""
        self.update_progress(InstallStep.CLEANUP, 95, "Cleaning up")
        
        tmp_dir = self.dotfiles_path / "tmp"
        if tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir)
                self.log_output("Cleaned temporary files\n")
            except Exception as e:
                self.log_output(f"Error cleaning temp files: {e}\n", True)
        
        return True
    
    def run_full_installation(self):
        """Run the complete installation process"""
        try:
            self.log_output("="*60 + "\n")
            self.log_output("🚀 Starting Dotfiles Installation\n")
            self.log_output("="*60 + "\n\n")
            
            # Step 1: Install yay
            if not self.install_yay():
                raise Exception("Failed to install yay")
            
            # Step 2: Install packages
            if not self.install_packages():
                raise Exception("Failed to install packages")
            
            # Step 3: Create directories
            if not self.setup_directories():
                raise Exception("Failed to create directories")
            
            # Step 4: Install fonts
            if not self.install_fonts():
                raise Exception("Failed to install fonts")
            
            # Step 5: Clone ZSH plugins
            if not self.clone_zsh_plugins():
                raise Exception("Failed to clone ZSH plugins")
            
            # Step 6: Setup ZSH
            if not self.setup_zsh():
                raise Exception("Failed to setup ZSH")
            
            # Step 7: Create symlinks
            if not self.create_symlinks():
                raise Exception("Failed to create symlinks")
            
            # Step 8: Setup system files (simplified)
            self.update_progress(InstallStep.SYSTEM_FILES, 82, "Setting up system files")
            self.log_output("System files setup placeholder (see bash script for details)\n")
            
            # Step 9: Setup gsettings
            if not self.setup_gsettings():
                raise Exception("Failed to setup gsettings")
            
            # Step 10: Setup kernel module
            if not self.setup_nct6687_module():
                self.log_output("Warning: Kernel module setup may have issues\n")
            
            # Step 11: Run nwg-displays
            if not self.run_nwg_displays():
                self.log_output("Warning: nwg-displays may have issues\n")
            
            # Step 12: Cleanup
            if not self.cleanup():
                self.log_output("Warning: Cleanup may have issues\n")
            
            # Final step
            self.update_progress(InstallStep.COMPLETE, 100, "Installation complete!")
            
            self.log_output("\n" + "="*60 + "\n")
            self.log_output("✅ Installation completed successfully!\n")
            self.log_output("="*60 + "\n")
            
            return True
            
        except Exception as e:
            self.log_output(f"\n❌ Installation failed: {str(e)}\n", True)
            self.update_progress(InstallStep.COMPLETE, 100, f"Installation failed: {str(e)}")
            return False
    
    def cancel_installation(self):
        """Cancel the running installation"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        self.running = False


class InstallerGUI(Gtk.Window):
    """Main GUI window for the installer"""
    
    def __init__(self):
        super().__init__(title="Dotfiles Installer")
        self.installer = None
        self.install_thread = None
        
        self.setup_ui()
        self.connect("destroy", self.on_destroy)
        self.set_default_size(800, 600)
        
    def setup_ui(self):
        """Setup the GUI interface"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_start(10)
        header_box.set_margin_end(10)
        header_box.set_margin_top(10)
        header_box.set_margin_bottom(10)
        
        icon = Gtk.Image.new_from_icon_name("system-software-install", Gtk.IconSize.DIALOG)
        header_box.pack_start(icon, False, False, 0)
        
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold'>Dotfiles Installer</span>")
        title_label.set_halign(Gtk.Align.START)
        header_box.pack_start(title_label, True, True, 0)
        
        main_box.pack_start(header_box, False, False, 0)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(separator, False, False, 0)
        
        # Progress area
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        progress_box.set_margin_start(10)
        progress_box.set_margin_end(10)
        progress_box.set_margin_top(10)
        progress_box.set_margin_bottom(5)
        
        # Progress label
        self.progress_label = Gtk.Label("Ready to install")
        self.progress_label.set_halign(Gtk.Align.START)
        progress_box.pack_start(self.progress_label, False, False, 0)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        progress_box.pack_start(self.progress_bar, False, False, 0)
        
        main_box.pack_start(progress_box, False, False, 0)
        
        # Terminal output area
        term_frame = Gtk.Frame(label="Installation Output")
        term_frame.set_margin_start(10)
        term_frame.set_margin_end(10)
        term_frame.set_margin_top(5)
        term_frame.set_margin_bottom(10)
        term_frame.set_shadow_type(Gtk.ShadowType.IN)
        
        # Create terminal using VTE
        self.terminal = Vte.Terminal()
        self.terminal.set_font(Pango.FontDescription("Monospace 10"))
        self.terminal.set_scrollback_lines(-1)  # Unlimited scrollback
        self.terminal.set_mouse_autohide(True)
        
        # Make terminal read-only for output display
        self.terminal.set_pty(Vte.Pty.new_sync(Vte.PtyFlags.DEFAULT))
        
        # Add terminal to scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.terminal)
        
        term_frame.add(scrolled)
        main_box.pack_start(term_frame, True, True, 0)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_margin_start(10)
        button_box.set_margin_end(10)
        button_box.set_margin_bottom(10)
        button_box.set_halign(Gtk.Align.END)
        
        # Start button
        self.start_button = Gtk.Button.new_with_label("Start Installation")
        self.start_button.get_style_context().add_class("suggested-action")
        self.start_button.connect("clicked", self.on_start_clicked)
        button_box.pack_start(self.start_button, False, False, 0)
        
        # Cancel button
        self.cancel_button = Gtk.Button.new_with_label("Cancel")
        self.cancel_button.set_sensitive(False)
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        button_box.pack_start(self.cancel_button, False, False, 0)
        
        # Close button
        self.close_button = Gtk.Button.new_with_label("Close")
        self.close_button.connect("clicked", self.on_close_clicked)
        button_box.pack_start(self.close_button, False, False, 0)
        
        main_box.pack_start(button_box, False, False, 0)
        
        # Status bar
        self.status_bar = Gtk.Statusbar()
        self.status_bar.push(0, "Ready")
        main_box.pack_start(self.status_bar, False, False, 0)
    
    def update_progress(self, step, progress, message=""):
        """Update progress display"""
        if isinstance(step, InstallStep):
            step_text = step.value
        else:
            step_text = str(step)
        
        if message:
            self.progress_label.set_text(f"{step_text}: {message}")
        else:
            self.progress_label.set_text(step_text)
        
        self.progress_bar.set_fraction(progress / 100)
        self.progress_bar.set_text(f"{progress:.1f}%")
        
        self.status_bar.push(0, f"{step_text} - {progress:.1f}%")
        
        return False
    
    def append_output(self, text, is_error=False):
        """Append text to terminal output"""
        buffer = self.terminal.get_buffer()
        
        # Get end iterator
        end_iter = buffer.get_end_iter()
        
        # Insert text
        buffer.insert(end_iter, text)
        
        # Scroll to end
        mark = buffer.create_mark(None, end_iter, True)
        self.terminal.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        
        # If error, we could change color, but VTE makes this complex
        # For now, just log it
        
        return False
    
    def gui_callback(self, *args):
        """Callback for installer to update GUI"""
        if args[0] == "output":
            text = args[1]
            is_error = args[2] if len(args) > 2 else False
            self.append_output(text, is_error)
        else:
            step = args[0]
            progress = args[1]
            message = args[2] if len(args) > 2 else ""
            self.update_progress(step, progress, message)
    
    def on_start_clicked(self, button):
        """Start installation"""
        # Create installer
        self.installer = DotfileInstaller(gui_callback=self.gui_callback)
        
        # Update UI state
        self.start_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.close_button.set_sensitive(False)
        
        # Clear terminal
        self.terminal.reset(True, True)
        
        # Start installation in separate thread
        self.install_thread = threading.Thread(target=self.run_installation)
        self.install_thread.daemon = True
        self.install_thread.start()
    
    def run_installation(self):
        """Run installation in background thread"""
        try:
            success = self.installer.run_full_installation()
            
            # Update UI after completion
            GLib.idle_add(self.on_installation_complete, success)
            
        except Exception as e:
            GLib.idle_add(self.append_output, f"\n❌ Unexpected error: {str(e)}\n", True)
            GLib.idle_add(self.on_installation_complete, False)
    
    def on_installation_complete(self, success):
        """Handle installation completion"""
        if success:
            self.append_output("\n✅ Installation completed successfully!\n")
            
            # Show reboot dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Installation Complete!"
            )
            dialog.format_secondary_text("Do you want to reboot now?")
            
            response = dialog.run()
            if response == Gtk.ResponseType.YES:
                subprocess.run("sudo reboot", shell=True)
            
            dialog.destroy()
        else:
            self.append_output("\n❌ Installation failed!\n", True)
        
        # Update button states
        self.start_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        self.close_button.set_sensitive(True)
        
        self.status_bar.push(0, "Installation complete" if success else "Installation failed")
    
    def on_cancel_clicked(self, button):
        """Cancel installation"""
        if self.installer:
            # Ask for confirmation
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Cancel Installation?"
            )
            dialog.format_secondary_text("Are you sure you want to cancel the installation?")
            
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self.installer.cancel_installation()
                self.append_output("\n⚠️ Installation cancelled by user\n")
                
                # Update button states
                self.start_button.set_sensitive(True)
                self.cancel_button.set_sensitive(False)
                self.close_button.set_sensitive(True)
                
                self.status_bar.push(0, "Installation cancelled")
    
    def on_close_clicked(self, button):
        """Close the application"""
        self.destroy()
    
    def on_destroy(self, widget):
        """Handle window destruction"""
        if self.installer:
            self.installer.cancel_installation()
        Gtk.main_quit()


def main():
    """Main entry point"""
    # Create and run application
    app = InstallerGUI()
    app.show_all()
    
    # Set application icon if available
    try:
        icon_theme = Gtk.IconTheme.get_default()
        if icon_theme.has_icon("system-software-install"):
            app.set_icon_name("system-software-install")
    except:
        pass
    
    Gtk.main()


if __name__ == "__main__":
    # Ensure we have required dependencies
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('Vte', '2.91')
    except ValueError as e:
        print(f"Missing required GTK/VTE versions: {e}")
        print("Please install: python-gobject vte3")
        sys.exit(1)
    
    main()
