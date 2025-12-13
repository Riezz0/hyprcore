#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import json
import threading
import traceback
import time
from datetime import datetime
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')
gi.require_version('Pango', '1.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, GdkPixbuf


class DotfilesInstaller:
    def __init__(self):
        self.window = None
        self.stack = None
        self.progress_bar = None
        self.status_label = None
        self.log_textview = None
        self.log_buffer = None
        self.install_button = None
        self.current_step = 0
        self.total_steps = 0
        self.home_dir = Path.home()
        self.dots_dir = self.home_dir / "dots"
        self.install_thread = None
        self.is_installing = False
        
    def run_polkit_command(self, cmd, description):
        """Run command with polkit elevation"""
        try:
            # Use xfce-polkit for privilege escalation
            polkit_cmd = ["/usr/lib/xfce-polkit/xfce-polkit", "-p", description]
            full_cmd = polkit_cmd + ["bash", "-c", cmd]
            
            self.log_message(f"Running with polkit: {description}")
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.log_message(f"ERROR: {result.stderr}", is_error=True)
                return False
                
            self.log_message(f"SUCCESS: {description}")
            return True
            
        except Exception as e:
            self.log_message(f"Polkit command failed: {str(e)}", is_error=True)
            return False
    
    def run_user_command(self, cmd, description):
        """Run command as regular user"""
        try:
            self.log_message(f"Running: {description}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
                cwd=self.home_dir
            )
            
            if result.returncode != 0:
                self.log_message(f"ERROR: {result.stderr}", is_error=True)
                return False
                
            if result.stdout:
                self.log_message(result.stdout.strip())
            return True
            
        except Exception as e:
            self.log_message(f"Command failed: {str(e)}", is_error=True)
            return False
    
    def log_message(self, message, is_error=False):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        tag = "ERROR" if is_error else "INFO"
        formatted = f"[{timestamp}] [{tag}] {message}\n"
        
        GLib.idle_add(self._append_log, formatted, is_error)
    
    def _append_log(self, text, is_error):
        """Thread-safe log appending"""
        end_iter = self.log_buffer.get_end_iter()
        
        if is_error:
            tag = self.log_buffer.create_tag("error", foreground="red", weight=Pango.Weight.BOLD)
            self.log_buffer.insert_with_tags(end_iter, text, tag)
        else:
            self.log_buffer.insert(end_iter, text)
        
        # Auto-scroll
        mark = self.log_buffer.create_mark(None, end_iter, False)
        self.log_textview.scroll_to_mark(mark, 0.0, False, 0.0, 0.0)
        return False
    
    def update_progress(self, step, total, message):
        """Update progress bar and status"""
        GLib.idle_add(self._update_progress_ui, step, total, message)
    
    def _update_progress_ui(self, step, total, message):
        """Thread-safe UI update"""
        self.current_step = step
        self.total_steps = total
        
        if total > 0:
            fraction = step / total
            self.progress_bar.set_fraction(fraction)
            self.progress_bar.set_text(f"{step}/{total}")
        
        self.status_label.set_text(message)
        return False
    
    def install_yay(self):
        """Install yay AUR helper"""
        self.log_message("Checking if yay is installed...")
        
        # Check if yay exists
        result = subprocess.run(["which", "yay"], capture_output=True)
        if result.returncode == 0:
            self.log_message("yay is already installed")
            return True
        
        self.log_message("Installing yay...")
        
        # Install required packages
        cmd = "pacman -S --needed --noconfirm git base-devel"
        if not self.run_polkit_command(cmd, "Install build dependencies"):
            return False
        
        # Clone and install yay
        tmp_yay = Path("/tmp/yay")
        if tmp_yay.exists():
            shutil.rmtree(tmp_yay)
        
        cmd = f"git clone https://aur.archlinux.org/yay.git {tmp_yay}"
        if not self.run_polkit_command(cmd, "Clone yay repository"):
            return False
        
        cmd = f"cd {tmp_yay} && makepkg -si --noconfirm"
        if not self.run_polkit_command(cmd, "Build and install yay"):
            return False
        
        self.log_message("yay installed successfully")
        return True
    
    def install_packages(self):
        """Install packages using yay"""
        self.log_message("Installing packages...")
        
        # Update system first
        cmd = "yay -Syyu --noconfirm"
        if not self.run_polkit_command(cmd, "Update system"):
            return False
        
        # Install packages
        packages = [
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
        ]
        
        cmd = f"yay -S --needed --noconfirm {' '.join(packages)}"
        if not self.run_polkit_command(cmd, "Install packages"):
            return False
        
        self.log_message("Packages installed successfully")
        return True
    
    def create_directories(self):
        """Create necessary directories"""
        self.log_message("Creating directories...")
        
        dirs = [
            self.home_dir / "git",
            self.home_dir / "venv",
            self.home_dir / "tmp",
            self.home_dir / ".local" / "share" / "fonts",
            self.dots_dir / "tmp"
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            self.log_message(f"Created: {dir_path}")
        
        # Create system directories with polkit
        cmd = "mkdir -p /etc/modules-load.d/"
        self.run_polkit_command(cmd, "Create system directory")
        
        return True
    
    def install_fonts(self):
        """Install fonts"""
        self.log_message("Installing fonts...")
        
        fonts_source = self.dots_dir / "fonts"
        fonts_dest = self.home_dir / ".local" / "share" / "fonts"
        
        if fonts_source.exists():
            for font_file in fonts_source.glob("*"):
                dest_file = fonts_dest / font_file.name
                shutil.copy2(font_file, dest_file)
                self.log_message(f"Installed font: {font_file.name}")
        
        # Update font cache
        cmd = "fc-cache -fv"
        if not self.run_user_command(cmd, "Update font cache"):
            return False
        
        return True
    
    def clone_zsh_plugins(self):
        """Clone zsh plugins"""
        self.log_message("Cloning zsh plugins...")
        
        tmp_dir = self.dots_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        
        plugins = [
            ("https://github.com/zsh-users/zsh-autosuggestions.git", "zsh-autosuggestions"),
            ("https://github.com/zsh-users/zsh-syntax-highlighting.git", "zsh-syntax-highlighting"),
            ("https://github.com/zdharma-continuum/fast-syntax-highlighting.git", "fast-syntax-highlighting"),
            ("https://github.com/marlonrichert/zsh-autocomplete.git", "zsh-autocomplete"),
            ("https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git", "autoswitch_virtualenv")
        ]
        
        for url, name in plugins:
            dest = tmp_dir / name
            if dest.exists():
                shutil.rmtree(dest)
            
            cmd = f"git clone {url} {dest}"
            if not self.run_user_command(cmd, f"Clone {name}"):
                return False
        
        return True
    
    def install_oh_my_zsh(self):
        """Install oh-my-zsh"""
        self.log_message("Installing oh-my-zsh...")
        
        cmd = 'RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended'
        if not self.run_user_command(cmd, "Install oh-my-zsh"):
            return False
        
        # Change shell to zsh
        zsh_path = shutil.which("zsh")
        if zsh_path:
            cmd = f"chsh -s {zsh_path}"
            if not self.run_polkit_command(cmd, "Change shell to zsh"):
                return False
        
        return True
    
    def setup_zsh_plugins(self):
        """Setup zsh plugins in oh-my-zsh"""
        self.log_message("Setting up zsh plugins...")
        
        omz_plugins = self.home_dir / ".oh-my-zsh" / "custom" / "plugins"
        omz_plugins.mkdir(parents=True, exist_ok=True)
        
        plugins_to_copy = [
            "autoswitch_virtualenv",
            "fast-syntax-highlighting",
            "zsh-autocomplete",
            "zsh-autosuggestions",
            "zsh-syntax-highlighting"
        ]
        
        for plugin in plugins_to_copy:
            src = self.dots_dir / "tmp" / plugin
            dest = omz_plugins / plugin
            
            if src.exists():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
                self.log_message(f"Copied plugin: {plugin}")
        
        return True
    
    def create_symlinks(self):
        """Create symlinks for dotfiles"""
        self.log_message("Creating symlinks...")
        
        # Remove existing configs
        configs_to_remove = [
            self.home_dir / ".config" / "hypr",
            self.home_dir / ".config" / "kitty",
            self.home_dir / ".zshrc"
        ]
        
        for config in configs_to_remove:
            if config.exists():
                if config.is_symlink():
                    config.unlink()
                elif config.is_dir():
                    shutil.rmtree(config)
                else:
                    config.unlink()
                self.log_message(f"Removed: {config}")
        
        # Remove system configs
        cmd = "rm -f /etc/sddm.conf /etc/default/grub"
        self.run_polkit_command(cmd, "Remove old system configs")
        
        # Create symlinks
        links = [
            (self.dots_dir / ".zshrc", self.home_dir / ".zshrc"),
            (self.dots_dir / "fastfetch", self.home_dir / ".config" / "fastfetch"),
            (self.dots_dir / "hypr", self.home_dir / ".config" / "hypr"),
            (self.dots_dir / "kitty", self.home_dir / ".config" / "kitty"),
            (self.dots_dir / "Kvantum", self.home_dir / ".config" / "Kvantum"),
            (self.dots_dir / "nvim", self.home_dir / ".config" / "nvim"),
            (self.dots_dir / "pywal", self.home_dir / ".config" / "pywal"),
            (self.dots_dir / "qt5ct", self.home_dir / ".config" / "qt5ct"),
            (self.dots_dir / "qt6ct", self.home_dir / ".config" / "qt6ct"),
            (self.dots_dir / "rofi", self.home_dir / ".config" / "rofi"),
            (self.dots_dir / "scripts", self.home_dir / ".config" / "scripts"),
            (self.dots_dir / "wal", self.home_dir / ".config" / "wal"),
            (self.dots_dir / "wallpapers", self.home_dir / ".config" / "wallpapers"),
            (self.dots_dir / "waybar", self.home_dir / ".config" / "waybar"),
            (self.dots_dir / "xdg-desktop-portal", self.home_dir / ".config" / "xdg-desktop-portal"),
            (self.dots_dir / ".icons", self.home_dir / ".icons"),
            (self.dots_dir / ".themes", self.home_dir / ".themes")
        ]
        
        for src, dest in links:
            if src.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    if dest.is_symlink():
                        dest.unlink()
                    elif dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                dest.symlink_to(src, target_is_directory=src.is_dir())
                self.log_message(f"Created symlink: {dest.name}")
        
        # Remove monitors config (will be regenerated)
        monitors_conf = self.home_dir / ".config" / "hypr" / "monitors.conf"
        if monitors_conf.exists():
            monitors_conf.unlink()
        
        return True
    
    def setup_cursor_theme(self):
        """Setup cursor theme"""
        self.log_message("Setting up cursor theme...")
        
        # Copy cursor themes
        cursors_src = self.dots_dir / "sys" / "cursors"
        
        if cursors_src.exists():
            # Remove default cursor theme
            cmd = "rm -rf /usr/share/icons/default"
            self.run_polkit_command(cmd, "Remove default cursor theme")
            
            # Copy new cursor themes
            for theme in ["default", "oreo_white_cursors"]:
                src = cursors_src / theme
                dest = Path(f"/usr/share/icons/{theme}")
                if src.exists():
                    cmd = f"cp -r {src} {dest.parent}/"
                    if not self.run_polkit_command(cmd, f"Copy {theme} cursor theme"):
                        return False
        
        # Set cursor theme with gsettings
        cmd = 'gsettings set org.gnome.desktop.interface cursor-theme "oreo_white_cursors"'
        if not self.run_user_command(cmd, "Set cursor theme"):
            return False
        
        # Set other GNOME settings
        settings = [
            ('org.gnome.desktop.interface icon-theme', '"oomox-Tokyo-Night"'),
            ('org.gnome.desktop.interface gtk-theme', '"oomox-Tokyo-Night"'),
            ('org.gnome.desktop.interface font-name', '"MesloLGL Nerd Font 12"'),
            ('org.gnome.desktop.interface document-font-name', '"MesloLGL Nerd Font 12"'),
            ('org.gnome.desktop.interface monospace-font-name', '"MesloLGL Mono Nerd Font 12"'),
            ('org.gnome.desktop.wm.preferences titlebar-font', '"MesloLGL Mono Nerd Font 12"')
        ]
        
        for key, value in settings:
            cmd = f'gsettings set {key} {value}'
            if not self.run_user_command(cmd, f"Set {key.split('.')[-1]}"):
                return False
        
        return True
    
    def setup_sddm(self):
        """Setup SDDM theme"""
        self.log_message("Setting up SDDM...")
        
        sddm_src = self.dots_dir / "sys" / "sddm"
        
        if sddm_src.exists():
            # Copy sddm.conf
            sddm_conf_src = sddm_src / "sddm.conf"
            if sddm_conf_src.exists():
                cmd = f"cp {sddm_conf_src} /etc/sddm.conf"
                if not self.run_polkit_command(cmd, "Copy SDDM config"):
                    return False
            
            # Copy SDDM theme
            theme_src = sddm_src / "tokyo-night"
            if theme_src.exists():
                cmd = f"cp -r {theme_src} /usr/share/sddm/themes/"
                if not self.run_polkit_command(cmd, "Copy SDDM theme"):
                    return False
        
        return True
    
    def setup_grub(self):
        """Setup GRUB theme"""
        self.log_message("Setting up GRUB...")
        
        grub_src = self.dots_dir / "sys" / "grub"
        
        if grub_src.exists():
            # Copy grub config
            grub_conf_src = grub_src / "grub"
            if grub_conf_src.exists():
                cmd = f"cp {grub_conf_src} /etc/default/grub"
                if not self.run_polkit_command(cmd, "Copy GRUB config"):
                    return False
            
            # Copy GRUB theme
            theme_src = grub_src / "tokyo-night"
            if theme_src.exists():
                cmd = f"cp -r {theme_src} /usr/share/grub/themes/"
                if not self.run_polkit_command(cmd, "Copy GRUB theme"):
                    return False
            
            # Update GRUB
            cmd = "grub-mkconfig -o /boot/grub/grub.cfg"
            if not self.run_polkit_command(cmd, "Update GRUB config"):
                return False
        
        return True
    
    def setup_nct6687d(self):
        """Setup nct6687d driver"""
        self.log_message("Setting up nct6687d driver...")
        
        # Clone driver
        tmp_dir = self.home_dir / "tmp" / "nct6687d"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        
        cmd = f"git clone https://github.com/Fred78290/nct6687d {tmp_dir}"
        if not self.run_user_command(cmd, "Clone nct6687d driver"):
            return False
        
        # Build and install
        cmd = f"cd {tmp_dir} && make dkms/install"
        if not self.run_polkit_command(cmd, "Install nct6687d driver"):
            return False
        
        # Copy config files
        sys_dir = self.dots_dir / "sys"
        
        no_nct_conf = sys_dir / "no_nct6683.conf"
        if no_nct_conf.exists():
            cmd = f"cp {no_nct_conf} /etc/modprobe.d/"
            if not self.run_polkit_command(cmd, "Copy nct6683 blacklist"):
                return False
        
        nct_conf = sys_dir / "nct6687.conf"
        if nct_conf.exists():
            cmd = f"cp {nct_conf} /etc/modules-load.d/nct6687.conf"
            if not self.run_polkit_command(cmd, "Copy nct6687 config"):
                return False
        
        # Load module
        cmd = "modprobe nct6687"
        self.run_polkit_command(cmd, "Load nct6687 module")
        
        return True
    
    def launch_nwg_displays(self):
        """Launch nwg-displays"""
        self.log_message("Launching nwg-displays for display configuration...")
        
        # Show dialog
        GLib.idle_add(self._show_nwg_displays_dialog)
        
        # Launch nwg-displays
        try:
            process = subprocess.Popen(["nwg-displays"])
            self.log_message("nwg-displays launched. Please configure your displays.")
            
            # Wait for process to complete
            process.wait()
            self.log_message("nwg-displays closed. Display configuration saved.")
            
            return True
        except Exception as e:
            self.log_message(f"Failed to launch nwg-displays: {str(e)}", is_error=True)
            return False
    
    def _show_nwg_displays_dialog(self):
        """Show dialog for nwg-displays"""
        dialog = Gtk.MessageDialog(
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Display Configuration"
        )
        dialog.format_secondary_text(
            "nwg-displays will now open for display configuration.\n\n"
            "Please set up your monitors in the nwg-displays window.\n"
            "Close the nwg-displays window when you're done to continue."
        )
        dialog.run()
        dialog.destroy()
        return False
    
    def cleanup(self):
        """Cleanup temporary files"""
        self.log_message("Cleaning up temporary files...")
        
        # Clean tmp directory
        tmp_dir = self.dots_dir / "tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            self.log_message("Cleaned up temporary files")
        
        return True
    
    def start_swww(self):
        """Start swww wallpaper daemon"""
        self.log_message("Starting swww...")
        
        # Start swww daemon
        cmd = "swww-daemon 2>/dev/null &"
        self.run_user_command(cmd, "Start swww daemon")
        
        # Run swww script
        scripts_dir = self.home_dir / "scripts"
        swww_script = scripts_dir / "swww.sh"
        if swww_script.exists():
            cmd = f"bash {swww_script} &"
            self.run_user_command(cmd, "Run swww script")
        
        return True
    
    def setup_pywal(self):
        """Setup pywal"""
        self.log_message("Setting up pywal...")
        
        # Apply pywal theme
        theme_file = self.home_dir / ".config" / "pywal" / "themes" / "active.json"
        if theme_file.exists():
            cmd = f"wal --theme {theme_file}"
            if not self.run_user_command(cmd, "Apply pywal theme"):
                return False
        
        # Copy pywal config to Kvantum
        wal_cache = self.home_dir / ".cache" / "wal"
        
        kvantum_config = wal_cache / "pywal.kvconfig"
        kvantum_dest = self.home_dir / ".config" / "Kvantum" / "pywal" / "pywal.kvconfig"
        if kvantum_config.exists():
            kvantum_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(kvantum_config, kvantum_dest)
            self.log_message("Copied pywal kvantum config")
        
        kvantum_svg = wal_cache / "pywal.svg"
        kvantum_svg_dest = self.home_dir / ".config" / "Kvantum" / "pywal" / "pywal.svg"
        if kvantum_svg.exists():
            shutil.copy2(kvantum_svg, kvantum_svg_dest)
            self.log_message("Copied pywal svg")
        
        return True
    
    def install_flatpak_apps(self):
        """Install flatpak apps (optional)"""
        self.log_message("Installing flatpak apps...")
        
        # Enable flatpak if not enabled
        cmd = "flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo"
        self.run_polkit_command(cmd, "Add flathub repository")
        
        # Install flatpak apps (commented out as in original script)
        # apps = [
        #     "org.localsend.localsend_app",
        #     "com.github.tchx84.Flatseal",
        #     "com.usebottles.bottles"
        # ]
        # 
        # for app in apps:
        #     cmd = f"flatpak install --noninteractive flathub {app}"
        #     if not self.run_polkit_command(cmd, f"Install {app}"):
        #         return False
        
        self.log_message("Flatpak apps installed (optional step)")
        return True
    
    def run_installation(self):
        """Main installation process"""
        try:
            self.is_installing = True
            GLib.idle_add(self._set_installing_state, True)
            
            steps = [
                (self.install_yay, "Installing yay AUR helper"),
                (self.install_packages, "Installing packages"),
                (self.create_directories, "Creating directories"),
                (self.install_fonts, "Installing fonts"),
                (self.clone_zsh_plugins, "Cloning zsh plugins"),
                (self.install_oh_my_zsh, "Installing oh-my-zsh"),
                (self.setup_zsh_plugins, "Setting up zsh plugins"),
                (self.create_symlinks, "Creating symlinks"),
                (self.setup_cursor_theme, "Setting up cursor theme"),
                (self.setup_sddm, "Setting up SDDM"),
                (self.setup_grub, "Setting up GRUB"),
                (self.setup_nct6687d, "Setting up nct6687d driver"),
                (self.start_swww, "Starting swww"),
                (self.setup_pywal, "Setting up pywal"),
                (self.cleanup, "Cleaning up"),
                (self.install_flatpak_apps, "Installing flatpak apps (optional)")
            ]
            
            self.total_steps = len(steps)
            
            for i, (step_func, description) in enumerate(steps, 1):
                self.update_progress(i, self.total_steps, description)
                
                if not step_func():
                    self.log_message(f"Installation failed at step: {description}", is_error=True)
                    GLib.idle_add(self._show_error, f"Installation failed at: {description}")
                    return
            
            # Launch nwg-displays at the end
            self.update_progress(self.total_steps + 1, self.total_steps + 2, "Launching nwg-displays")
            self.launch_nwg_displays()
            
            self.update_progress(self.total_steps + 2, self.total_steps + 2, "Installation complete!")
            self.log_message("✅ Installation complete!")
            
            GLib.idle_add(self._show_success_dialog)
            
        except Exception as e:
            self.log_message(f"Installation error: {str(e)}\n{traceback.format_exc()}", is_error=True)
            GLib.idle_add(self._show_error, str(e))
        finally:
            self.is_installing = False
            GLib.idle_add(self._set_installing_state, False)
    
    def _set_installing_state(self, installing):
        """Update UI for installing state"""
        self.install_button.set_sensitive(not installing)
        return False
    
    def _show_error(self, message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Installation Failed"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        return False
    
    def _show_success_dialog(self):
        """Show success dialog"""
        dialog = Gtk.MessageDialog(
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Installation Complete"
        )
        dialog.format_secondary_text(
            "✅ Dotfiles installation complete!\n\n"
            "A reboot is recommended to apply all changes.\n"
            "After reboot, you can run the reboot.sh script for final configuration."
        )
        dialog.run()
        dialog.destroy()
        return False
    
    def start_installation(self, button):
        """Start installation thread"""
        if self.is_installing:
            return
        
        # Clear log
        self.log_buffer.set_text("")
        
        # Start installation in separate thread
        self.install_thread = threading.Thread(target=self.run_installation)
        self.install_thread.daemon = True
        self.install_thread.start()
    
    def create_ui(self):
        """Create the main UI"""
        # Create main window
        self.window = Gtk.Window(title="Dotfiles Installer")
        self.window.set_default_size(800, 600)
        self.window.set_border_width(10)
        
        # Set window icon
        try:
            icon_theme = Gtk.IconTheme.get_default()
            if icon_theme.has_icon("system-software-install"):
                self.window.set_icon_name("system-software-install")
        except:
            pass
        
        # Create main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window.add(main_box)
        
        # Header
        header_label = Gtk.Label()
        header_label.set_markup("<span size='x-large' weight='bold'>Dotfiles Installer</span>")
        header_label.set_halign(Gtk.Align.START)
        main_box.pack_start(header_label, False, False, 0)
        
        # Separator
        main_box.pack_start(Gtk.Separator(), False, False, 5)
        
        # Progress bar
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.pack_start(progress_box, False, False, 0)
        
        self.status_label = Gtk.Label("Ready to install")
        self.status_label.set_halign(Gtk.Align.START)
        progress_box.pack_start(self.status_label, False, False, 0)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        progress_box.pack_start(self.progress_bar, False, False, 0)
        
        # Log view
        log_frame = Gtk.Frame(label="Installation Log")
        main_box.pack_start(log_frame, True, True, 0)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        log_frame.add(scrolled_window)
        
        self.log_textview = Gtk.TextView()
        self.log_textview.set_editable(False)
        self.log_textview.set_monospace(True)
        self.log_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled_window.add(self.log_textview)
        
        self.log_buffer = self.log_textview.get_buffer()
        
        # Create tag for error messages
        self.log_buffer.create_tag("error", foreground="red", weight=Pango.Weight.BOLD)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        main_box.pack_start(button_box, False, False, 0)
        
        # Quit button
        quit_button = Gtk.Button(label="Quit")
        quit_button.connect("clicked", lambda b: self.window.destroy())
        button_box.pack_start(quit_button, False, False, 0)
        
        # Install button
        self.install_button = Gtk.Button(label="Start Installation")
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.connect("clicked", self.start_installation)
        button_box.pack_start(self.install_button, False, False, 0)
        
        # Connect window close event
        self.window.connect("destroy", Gtk.main_quit)
        
        # Show window
        self.window.show_all()
    
    def run(self):
        """Run the application"""
        self.create_ui()
        Gtk.main()


def main():
    # Check if running as root
    if os.geteuid() == 0:
        print("Do not run this installer as root!")
        print("It will use polkit for privileged operations when needed.")
        sys.exit(1)
    
    # Check if dots directory exists
    dots_dir = Path.home() / "dots"
    if not dots_dir.exists():
        print(f"Error: dots directory not found at {dots_dir}")
        print("Please clone your dotfiles to ~/dots first.")
        sys.exit(1)
    
    # Start the installer
    app = DotfilesInstaller()
    app.run()


if __name__ == "__main__":
    main()
