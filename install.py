#!/usr/bin/env python3
"""
PyGObject Dotfiles Installer
A Python-based installer for dotfiles using PyGObject for GUI interactions.
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from enum import Enum
import signal
import threading
import time

# Try to import GTK components
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib, Gio, Pango
    GTK_AVAILABLE = True
except ImportError:
    GTK_AVAILABLE = False
    print("PyGObject/GTK not available. Running in CLI mode.")


class InstallStep(Enum):
    """Installation steps enumeration"""
    PREPARE = "prepare"
    DEPENDENCIES = "dependencies"
    DOTFILES = "dotfiles"
    CONFIGURATION = "configuration"
    FINALIZE = "finalize"


class DotfileInstaller:
    """Main installer class for managing dotfiles installation"""
    
    def __init__(self, dotfiles_path=None):
        self.dotfiles_path = dotfiles_path or Path.home() / "dots"
        self.user = os.getenv("USER")
        self.home = Path.home()
        self.log_file = self.home / ".dotfiles-install.log"
        self.config = self.load_config()
        self.current_step = InstallStep.PREPARE
        self.progress = 0
        self.running = True
        
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
                    "https://github.com/zsh-users/zsh-autosuggestions.git",
                    "https://github.com/zsh-users/zsh-syntax-highlighting.git",
                    "https://github.com/zdharma-continuum/fast-syntax-highlighting.git",
                    "https://github.com/marlonrichert/zsh-autocomplete.git",
                    "https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git"
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
            ],
            "system_files": {
                "cursors": {
                    "default": "/usr/share/icons/default",
                    "oreo_white_cursors": "/usr/share/icons/oreo_white_cursors"
                },
                "sddm": {
                    "config": "/etc/sddm.conf",
                    "theme": "/usr/share/sddm/themes/tokyo-night/"
                },
                "grub": {
                    "config": "/etc/default/grub",
                    "theme": "/usr/share/grub/themes/tokyo-night/"
                },
                "modules": {
                    "nct6687": "/etc/modules-load.d/nct6687.conf",
                    "no_nct6683": "/etc/modprobe.d/no_nct6683.conf"
                }
            }
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return {**default_config, **json.load(f)}
            except:
                return default_config
        return default_config
    
    def log(self, message, level="INFO"):
        """Log messages to file and console"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        print(f"[{level}] {message}")
        
    def run_command(self, cmd, check=True, capture_output=False):
        """Run shell command with error handling"""
        self.log(f"Running command: {cmd}")
        
        try:
            if capture_output:
                result = subprocess.run(cmd, shell=True, check=check, 
                                      capture_output=True, text=True)
                return result.stdout.strip()
            else:
                subprocess.run(cmd, shell=True, check=check)
                return True
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", "ERROR")
            if check:
                raise
            return False
    
    def update_progress(self, step, progress):
        """Update progress for GUI"""
        self.current_step = step
        self.progress = progress
        if GTK_AVAILABLE:
            GLib.idle_add(self.on_progress_update, step, progress)
    
    def install_yay(self):
        """Install yay AUR helper if not present"""
        self.log("Checking for yay installation...")
        
        if not self.run_command("command -v yay", check=False, capture_output=True):
            self.log("Installing yay...")
            self.run_command("sudo pacman -S --needed --noconfirm git base-devel")
            self.run_command("git clone https://aur.archlinux.org/yay.git /tmp/yay")
            self.run_command("cd /tmp/yay && makepkg -si --noconfirm")
            self.log("yay installed successfully")
        else:
            self.log("yay already installed")
    
    def install_packages(self):
        """Install packages using yay"""
        self.log("Updating package database...")
        self.run_command("yay -Syyu")
        
        self.log("Installing packages...")
        packages = " ".join(self.config["packages"]["yay_packages"])
        self.run_command(f"yay -S --needed --noconfirm {packages}")
    
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            self.home / "git",
            self.home / "venv",
            self.home / "tmp",
            self.home / ".local" / "share" / "fonts",
            self.home / ".oh-my-zsh" / "custom" / "plugins",
            self.dotfiles_path / "tmp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.run_command("sudo mkdir -p /etc/modules-load.d/")
    
    def install_fonts(self):
        """Install custom fonts"""
        fonts_src = self.dotfiles_path / "fonts"
        fonts_dst = self.home / ".local" / "share" / "fonts"
        
        if fonts_src.exists():
            self.log("Installing fonts...")
            for font_file in fonts_src.glob("*"):
                shutil.copy2(font_file, fonts_dst)
            self.run_command("fc-cache -fv")
    
    def clone_zsh_plugins(self):
        """Clone ZSH plugins"""
        tmp_dir = self.dotfiles_path / "tmp"
        repos = self.config["repositories"]["zsh_plugins"]
        
        for repo_url in repos:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            repo_path = tmp_dir / repo_name
            
            self.log(f"Cloning {repo_name}...")
            if repo_url == "https://github.com/marlonrichert/zsh-autocomplete.git":
                self.run_command(f"git clone --depth 1 -- {repo_url} {repo_path}")
            else:
                self.run_command(f"git clone {repo_url} {repo_path}")
    
    def setup_zsh(self):
        """Setup ZSH with Oh My Zsh"""
        self.log("Installing Oh My Zsh...")
        self.run_command('RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended')
        
        self.log("Setting ZSH as default shell...")
        self.run_command(f"chsh -s {shutil.which('zsh')}")
        
        # Copy ZSH plugins
        tmp_dir = self.dotfiles_path / "tmp"
        plugins_dir = self.home / ".oh-my-zsh" / "custom" / "plugins"
        
        for plugin_dir in tmp_dir.iterdir():
            if plugin_dir.is_dir():
                shutil.copytree(plugin_dir, plugins_dir / plugin_dir.name, 
                              dirs_exist_ok=True)
    
    def create_symlinks(self):
        """Create symbolic links for dotfiles"""
        self.log("Creating symlinks...")
        
        # Remove existing configs
        configs_to_remove = [
            self.home / ".config" / "hypr",
            self.home / ".config" / "kitty",
            self.home / ".zshrc"
        ]
        
        for config in configs_to_remove:
            if config.exists():
                if config.is_symlink():
                    config.unlink()
                else:
                    shutil.rmtree(config)
        
        # Create symlinks
        for link in self.config["symlinks"]:
            src = self.dotfiles_path / link.strip('/')
            dst = self.home / link.strip('/')
            
            if src.exists():
                # Ensure parent directory exists
                dst.parent.mkdir(parents=True, exist_ok=True)
                
                if dst.exists():
                    if dst.is_symlink():
                        dst.unlink()
                    else:
                        if dst.is_dir():
                            shutil.rmtree(dst)
                        else:
                            dst.unlink()
                
                self.log(f"Linking {src} -> {dst}")
                dst.symlink_to(src, target_is_directory=src.is_dir())
    
    def setup_system_files(self):
        """Copy system configuration files"""
        self.log("Setting up system files...")
        
        # Copy cursor themes
        cursors_src = self.dotfiles_path / "sys" / "cursors"
        if cursors_src.exists():
            for cursor_theme in ["default", "oreo_white_cursors"]:
                src = cursors_src / cursor_theme
                dst = Path(self.config["system_files"]["cursors"][cursor_theme])
                if src.exists():
                    self.run_command(f"sudo cp -r {src} {dst}")
        
        # Setup SDDM
        sddm_src = self.dotfiles_path / "sys" / "sddm"
        if sddm_src.exists():
            self.run_command(f"sudo cp -r {sddm_src}/sddm.conf /etc/")
            self.run_command(f"sudo cp -r {sddm_src}/tokyo-night/ /usr/share/sddm/themes/")
        
        # Setup GRUB
        grub_src = self.dotfiles_path / "sys" / "grub"
        if grub_src.exists():
            self.run_command(f"sudo cp -r {grub_src}/grub /etc/default/")
            self.run_command(f"sudo cp -r {grub_src}/tokyo-night /usr/share/grub/themes/")
            self.run_command("sudo grub-mkconfig -o /boot/grub/grub.cfg")
        
        # Setup modules
        modules_src = self.dotfiles_path / "sys"
        if modules_src.exists():
            self.run_command(f"sudo cp -r {modules_src}/no_nct6683.conf /etc/modprobe.d/")
            self.run_command(f"sudo cp -r {modules_src}/nct6687.conf /etc/modules-load.d/nct6687.conf")
    
    def setup_gsettings(self):
        """Configure GNOME settings"""
        self.log("Configuring GNOME settings...")
        
        settings = {
            "org.gnome.desktop.interface cursor-theme": "oreo_white_cursors",
            "org.gnome.desktop.interface icon-theme": "oomox-Tokyo-Night",
            "org.gnome.desktop.interface gtk-theme": "oomox-Tokyo-Night",
            "org.gnome.desktop.interface font-name": "MesloLGL Nerd Font 12",
            "org.gnome.desktop.interface document-font-name": "MesloLGL Nerd Font 12",
            "org.gnome.desktop.interface monospace-font-name": "MesloLGL Mono Nerd Font 12",
            "org.gnome.desktop.wm.preferences titlebar-font": "MesloLGL Mono Nerd Font 12"
        }
        
        for key, value in settings.items():
            self.run_command(f'gsettings set {key} "{value}"')
    
    def setup_nct6687_module(self):
        """Setup NCT6687 kernel module"""
        self.log("Setting up NCT6687 kernel module...")
        
        module_dir = self.home / "tmp" / "nct6687d"
        self.run_command("git clone https://github.com/Fred78290/nct6687d " + str(module_dir))
        
        if module_dir.exists():
            self.run_command(f"cd {module_dir} && make dkms/install")
            self.run_command("sudo modprobe nct6687")
    
    def run_nwg_displays(self):
        """Run nwg-displays for monitor configuration"""
        self.log("Launching nwg-displays for display configuration...")
        print("\n" + "="*60)
        print("🚀 Launching nwg-displays for display configuration...")
        print("📺 Please set up your monitors in the nwg-displays window.")
        print("❌ Close the nwg-displays window when you're done to continue...")
        print("="*60 + "\n")
        
        subprocess.run("nwg-displays", shell=True)
        
        print("✅ Display configuration saved! Continuing with setup...")
    
    def cleanup(self):
        """Clean up temporary files"""
        tmp_dir = self.dotfiles_path / "tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
    
    def run_installation(self):
        """Run the complete installation process"""
        try:
            self.update_progress(InstallStep.PREPARE, 10)
            self.install_yay()
            
            self.update_progress(InstallStep.DEPENDENCIES, 30)
            self.install_packages()
            self.setup_directories()
            
            self.update_progress(InstallStep.DOTFILES, 50)
            self.install_fonts()
            self.clone_zsh_plugins()
            self.setup_zsh()
            self.create_symlinks()
            
            self.update_progress(InstallStep.CONFIGURATION, 70)
            self.setup_system_files()
            self.setup_gsettings()
            self.setup_nct6687_module()
            
            self.update_progress(InstallStep.FINALIZE, 90)
            self.run_nwg_displays()
            self.cleanup()
            
            self.update_progress(InstallStep.FINALIZE, 100)
            self.log("Installation completed successfully!")
            
            # Ask about reboot
            if GTK_AVAILABLE:
                GLib.idle_add(self.show_reboot_dialog)
            else:
                response = input("\nInstallation complete! Reboot now? (y/N): ")
                if response.lower() == 'y':
                    self.run_command("sudo reboot")
            
        except Exception as e:
            self.log(f"Installation failed: {e}", "ERROR")
            if GTK_AVAILABLE:
                GLib.idle_add(self.show_error_dialog, str(e))
            raise
    
    # GUI methods (only used if GTK is available)
    def on_progress_update(self, step, progress):
        """Update progress in GUI (to be implemented in GUI class)"""
        pass
    
    def show_reboot_dialog(self):
        """Show reboot dialog (to be implemented in GUI class)"""
        pass
    
    def show_error_dialog(self, error_message):
        """Show error dialog (to be implemented in GUI class)"""
        pass


class InstallerGUI(Gtk.Window):
    """GTK GUI for the dotfiles installer"""
    
    def __init__(self, installer):
        super().__init__(title="Dotfiles Installer")
        self.installer = installer
        self.installer.on_progress_update = self.on_progress_update
        self.installer.show_reboot_dialog = self.show_reboot_dialog
        self.installer.show_error_dialog = self.show_error_dialog
        
        self.setup_ui()
        self.connect("destroy", Gtk.main_quit)
        
    def setup_ui(self):
        """Setup the GUI interface"""
        self.set_default_size(600, 400)
        self.set_border_width(10)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)
        
        # Header
        header = Gtk.Label()
        header.set_markup("<span size='x-large' weight='bold'>Dotfiles Installer</span>")
        header.set_justify(Gtk.Justification.CENTER)
        main_box.pack_start(header, False, False, 10)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        main_box.pack_start(self.progress_bar, False, False, 5)
        
        # Status label
        self.status_label = Gtk.Label("Preparing installation...")
        self.status_label.set_justify(Gtk.Justification.LEFT)
        main_box.pack_start(self.status_label, False, False, 5)
        
        # Log view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_buffer = self.log_view.get_buffer()
        
        scrolled.add(self.log_view)
        main_box.pack_start(scrolled, True, True, 5)
        
        # Buttons
        button_box = Gtk.Box(spacing=6)
        main_box.pack_start(button_box, False, False, 0)
        
        self.start_button = Gtk.Button(label="Start Installation")
        self.start_button.connect("clicked", self.on_start_clicked)
        button_box.pack_start(self.start_button, True, True, 0)
        
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        button_box.pack_start(self.cancel_button, True, True, 0)
        
    def on_progress_update(self, step, progress):
        """Update progress bar and status"""
        self.progress_bar.set_fraction(progress / 100)
        self.progress_bar.set_text(f"{step.value.title()}... {progress}%")
        self.status_label.set_text(f"Current step: {step.value.replace('_', ' ').title()}")
        
        # Add to log
        iter_end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(iter_end, f"[{step.value.upper()}] Progress: {progress}%\n")
        
        # Scroll to end
        mark = self.log_buffer.create_mark(None, iter_end, True)
        self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        
        return False  # GLib.idle_add expects False
    
    def on_start_clicked(self, button):
        """Start the installation process"""
        button.set_sensitive(False)
        self.cancel_button.set_sensitive(False)
        
        # Run installation in separate thread
        thread = threading.Thread(target=self.installer.run_installation)
        thread.daemon = True
        thread.start()
    
    def on_cancel_clicked(self, button):
        """Cancel the installation"""
        self.installer.running = False
        Gtk.main_quit()
    
    def show_reboot_dialog(self):
        """Show reboot confirmation dialog"""
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
        Gtk.main_quit()
        return False
    
    def show_error_dialog(self, error_message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Installation Failed!"
        )
        dialog.format_secondary_text(f"Error: {error_message}")
        
        dialog.run()
        dialog.destroy()
        return False


def main():
    """Main entry point"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Dotfiles Installer")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode only")
    parser.add_argument("--dotfiles", help="Path to dotfiles directory")
    args = parser.parse_args()
    
    # Create installer instance
    installer = DotfileInstaller(args.dotfiles)
    
    # Run in GUI mode if available and not forced CLI
    if GTK_AVAILABLE and not args.cli:
        app = InstallerGUI(installer)
        app.show_all()
        Gtk.main()
    else:
        # Run in CLI mode
        print("="*60)
        print("Dotfiles Installer - CLI Mode")
        print("="*60)
        
        try:
            installer.run_installation()
        except KeyboardInterrupt:
            print("\nInstallation cancelled by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\nInstallation failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
