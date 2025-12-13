#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import json
import threading
import traceback
import time
import select
import fcntl
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
        
    def run_polkit_command(self, cmd, description, timeout=300):
        """Run command with polkit elevation - improved version"""
        try:
            # Use pkexec for better compatibility
            full_cmd = ["pkexec", "bash", "-c", cmd]
            
            self.log_message(f"Running with elevated privileges: {description}")
            
            # Run command with timeout
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Set non-blocking reads
            for pipe in [process.stdout, process.stderr]:
                if pipe:
                    fd = pipe.fileno()
                    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            # Read output in real-time
            start_time = time.time()
            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.terminate()
                    self.log_message(f"Command timed out after {timeout} seconds", is_error=True)
                    return False
                
                # Check if process finished
                if process.poll() is not None:
                    break
                
                # Read output
                for pipe in [process.stdout, process.stderr]:
                    if pipe:
                        try:
                            output = pipe.read()
                            if output:
                                for line in output.split('\n'):
                                    if line.strip():
                                        self.log_message(f"[sudo] {line.strip()}")
                        except:
                            pass
                
                time.sleep(0.1)
            
            # Get remaining output
            stdout, stderr = process.communicate()
            
            if stdout:
                for line in stdout.split('\n'):
                    if line.strip():
                        self.log_message(line.strip())
            
            if process.returncode != 0:
                if stderr:
                    for line in stderr.split('\n'):
                        if line.strip():
                            self.log_message(f"ERROR: {line.strip()}", is_error=True)
                return False
            
            self.log_message(f"SUCCESS: {description}")
            return True
            
        except Exception as e:
            self.log_message(f"Command failed: {str(e)}", is_error=True)
            return False
    
    def run_user_command(self, cmd, description, timeout=120):
        """Run command as regular user with timeout"""
        try:
            self.log_message(f"Running: {description}")
            
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.home_dir
            )
            
            # Set non-blocking reads
            for pipe in [process.stdout, process.stderr]:
                if pipe:
                    fd = pipe.fileno()
                    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            # Read output in real-time
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    process.terminate()
                    self.log_message(f"Command timed out after {timeout} seconds", is_error=True)
                    return False
                
                if process.poll() is not None:
                    break
                
                for pipe in [process.stdout, process.stderr]:
                    if pipe:
                        try:
                            output = pipe.read()
                            if output:
                                for line in output.split('\n'):
                                    if line.strip():
                                        self.log_message(line.strip())
                        except:
                            pass
                
                time.sleep(0.1)
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                if stderr:
                    for line in stderr.split('\n'):
                        if line.strip():
                            self.log_message(f"ERROR: {line.strip()}", is_error=True)
                return False
            
            return True
            
        except Exception as e:
            self.log_message(f"Command failed: {str(e)}", is_error=True)
            return False
    
    def check_yay_installed(self):
        """Check if yay is installed"""
        try:
            result = subprocess.run(
                ["which", "yay"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def install_yay(self):
        """Install yay AUR helper - improved version"""
        self.log_message("Checking if yay is installed...")
        
        if self.check_yay_installed():
            self.log_message("yay is already installed")
            return True
        
        self.log_message("Installing yay...")
        
        # Step 1: Install git and base-devel
        self.log_message("Installing build dependencies...")
        cmd = "pacman -S --needed --noconfirm git base-devel"
        if not self.run_polkit_command(cmd, "Install build dependencies"):
            return False
        
        # Step 2: Create temporary directory
        tmp_yay = Path("/tmp/yay_install")
        if tmp_yay.exists():
            shutil.rmtree(tmp_yay)
        tmp_yay.mkdir(parents=True, exist_ok=True)
        
        # Step 3: Clone yay
        self.log_message("Cloning yay repository...")
        clone_cmd = "git clone https://aur.archlinux.org/yay.git ."
        if not self.run_user_command(f"cd {tmp_yay} && {clone_cmd}", "Clone yay"):
            # Alternative: Download manually
            self.log_message("Trying alternative installation method...")
            download_cmd = "curl -L https://github.com/Jguer/yay/releases/latest/download/yay_linux_amd64.tar.gz | tar xz"
            if not self.run_polkit_command(f"cd /tmp && {download_cmd} && mv yay_linux_amd64/yay /usr/local/bin/", "Download yay binary"):
                return False
            # Make it executable
            self.run_polkit_command("chmod +x /usr/local/bin/yay", "Make yay executable")
            self.log_message("yay installed via binary")
            return True
        
        # Step 4: Build and install
        self.log_message("Building yay...")
        build_cmd = f"cd {tmp_yay} && makepkg -si --noconfirm"
        if not self.run_polkit_command(build_cmd, "Build and install yay"):
            # Try with sudo instead
            self.log_message("Trying with makepkg directly...")
            build_cmd = f"cd {tmp_yay} && makepkg -si"
            process = subprocess.Popen(
                ["sudo", "bash", "-c", build_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log_message(f"Failed to install yay: {stderr}", is_error=True)
                return False
        
        # Verify installation
        if self.check_yay_installed():
            self.log_message("yay installed successfully")
            return True
        else:
            self.log_message("yay installation may have failed", is_error=True)
            return False
    
    def install_packages(self):
        """Install packages using yay - improved version"""
        self.log_message("Installing packages...")
        
        # First, check if we can run yay
        if not self.check_yay_installed():
            self.log_message("yay not found, trying to install it first", is_error=True)
            return False
        
        # Step 1: Update package database (non-interactive)
        self.log_message("Updating package databases...")
        update_cmd = "yay -Sy --noconfirm"
        if not self.run_user_command(update_cmd, "Update package databases"):
            self.log_message("Warning: Failed to update databases, continuing anyway...")
        
        # Step 2: Install packages in batches to avoid timeouts
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
        
        # Split into smaller batches
        batch_size = 10
        for i in range(0, len(packages), batch_size):
            batch = packages[i:i + batch_size]
            self.log_message(f"Installing batch {i//batch_size + 1}/{(len(packages)-1)//batch_size + 1}")
            
            cmd = f"yay -S --needed --noconfirm {' '.join(batch)}"
            if not self.run_polkit_command(cmd, f"Install packages batch {i//batch_size + 1}"):
                # Try alternative method for AUR packages
                self.log_message("Trying alternative installation method...")
                for pkg in batch:
                    single_cmd = f"yay -S --needed --noconfirm {pkg}"
                    if not self.run_polkit_command(single_cmd, f"Install {pkg}"):
                        self.log_message(f"Warning: Failed to install {pkg}, skipping...", is_error=True)
        
        self.log_message("Package installation completed")
        return True
    
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
                try:
                    shutil.copy2(font_file, dest_file)
                    self.log_message(f"Installed font: {font_file.name}")
                except Exception as e:
                    self.log_message(f"Failed to copy font {font_file.name}: {e}", is_error=True)
        
        # Update font cache
        cmd = "fc-cache -fv"
        if not self.run_user_command(cmd, "Update font cache"):
            self.log_message("Warning: Font cache update failed", is_error=True)
        
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
                self.log_message(f"Warning: Failed to clone {name}, continuing...", is_error=True)
        
        return True
    
    def install_oh_my_zsh(self):
        """Install oh-my-zsh"""
        self.log_message("Installing oh-my-zsh...")
        
        # Check if oh-my-zsh is already installed
        omz_dir = self.home_dir / ".oh-my-zsh"
        if omz_dir.exists():
            self.log_message("oh-my-zsh is already installed")
            return True
        
        # Download and install oh-my-zsh
        install_cmd = 'RUNZSH=no sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended'
        if not self.run_user_command(install_cmd, "Install oh-my-zsh"):
            # Try alternative method
            self.log_message("Trying alternative oh-my-zsh installation...")
            clone_cmd = 'git clone https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh'
            cp_cmd = 'cp ~/.oh-my-zsh/templates/zshrc.zsh-template ~/.zshrc'
            if not self.run_user_command(clone_cmd, "Clone oh-my-zsh"):
                return False
            if not self.run_user_command(cp_cmd, "Copy zshrc template"):
                return False
        
        # Change shell to zsh
        zsh_path = shutil.which("zsh")
        if zsh_path:
            cmd = f"chsh -s {zsh_path}"
            if not self.run_polkit_command(cmd, "Change shell to zsh"):
                self.log_message("Warning: Failed to change shell, you can do it manually later")
        
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
                try:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(src, dest)
                    self.log_message(f"Copied plugin: {plugin}")
                except Exception as e:
                    self.log_message(f"Failed to copy plugin {plugin}: {e}", is_error=True)
        
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
                try:
                    if config.is_symlink():
                        config.unlink()
                    elif config.is_dir():
                        shutil.rmtree(config)
                    else:
                        config.unlink()
                    self.log_message(f"Removed: {config}")
                except Exception as e:
                    self.log_message(f"Failed to remove {config}: {e}", is_error=True)
        
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
                try:
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
                except Exception as e:
                    self.log_message(f"Failed to create symlink for {src.name}: {e}", is_error=True)
        
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
            # Copy new cursor themes
            for theme in ["default", "oreo_white_cursors"]:
                src = cursors_src / theme
                if src.exists():
                    cmd = f"cp -r {src} /usr/share/icons/"
                    if not self.run_polkit_command(cmd, f"Copy {theme} cursor theme"):
                        self.log_message(f"Warning: Failed to copy {theme} cursor theme", is_error=True)
        
        # Set cursor theme with gsettings
        cmds = [
            'gsettings set org.gnome.desktop.interface cursor-theme "oreo_white_cursors"',
            'gsettings set org.gnome.desktop.interface icon-theme "oomox-Tokyo-Night"',
            'gsettings set org.gnome.desktop.interface gtk-theme "oomox-Tokyo-Night"',
            'gsettings set org.gnome.desktop.interface font-name "MesloLGL Nerd Font 12"',
            'gsettings set org.gnome.desktop.interface document-font-name "MesloLGL Nerd Font 12"',
            'gsettings set org.gnome.desktop.interface monospace-font-name "MesloLGL Mono Nerd Font 12"',
            'gsettings set org.gnome.desktop.wm.preferences titlebar-font "MesloLGL Mono Nerd Font 12"'
        ]
        
        for cmd in cmds:
            if not self.run_user_command(cmd, "Set GNOME setting"):
                self.log_message("Warning: Failed to set GNOME setting", is_error=True)
        
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
                    self.log_message("Warning: Failed to copy SDDM config", is_error=True)
            
            # Copy SDDM theme
            theme_src = sddm_src / "tokyo-night"
            if theme_src.exists():
                cmd = f"cp -r {theme_src} /usr/share/sddm/themes/"
                if not self.run_polkit_command(cmd, "Copy SDDM theme"):
                    self.log_message("Warning: Failed to copy SDDM theme", is_error=True)
        
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
                    self.log_message("Warning: Failed to copy GRUB config", is_error=True)
            
            # Copy GRUB theme
            theme_src = grub_src / "tokyo-night"
            if theme_src.exists():
                cmd = f"cp -r {theme_src} /usr/share/grub/themes/"
                if not self.run_polkit_command(cmd, "Copy GRUB theme"):
                    self.log_message("Warning: Failed to copy GRUB theme", is_error=True)
            
            # Update GRUB
            cmd = "grub-mkconfig -o /boot/grub/grub.cfg"
            if not self.run_polkit_command(cmd, "Update GRUB config"):
                self.log_message("Warning: Failed to update GRUB config", is_error=True)
        
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
            self.log_message("Warning: Failed to clone nct6687d driver", is_error=True)
            return True  # Continue anyway
        
        # Build and install
        cmd = f"cd {tmp_dir} && make dkms/install"
        if not self.run_polkit_command(cmd, "Install nct6687d driver"):
            self.log_message("Warning: Failed to install nct6687d driver", is_error=True)
        
        # Copy config files
        sys_dir = self.dots_dir / "sys"
        
        no_nct_conf = sys_dir / "no_nct6683.conf"
        if no_nct_conf.exists():
            cmd = f"cp {no_nct_conf} /etc/modprobe.d/"
            self.run_polkit_command(cmd, "Copy nct6683 blacklist")
        
        nct_conf = sys_dir / "nct6687.conf"
        if nct_conf.exists():
            cmd = f"cp {nct_conf} /etc/modules-load.d/nct6687.conf"
            self.run_polkit_command(cmd, "Copy nct6687 config")
        
        return True
    
    def launch_nwg_displays(self):
        """Launch nwg-displays"""
        self.log_message("Launching nwg-displays for display configuration...")
        
        # Show dialog
        GLib.idle_add(self._show_nwg_displays_dialog)
        
        # Launch nwg-displays
        try:
            self.log_message("Starting nwg-displays...")
            process = subprocess.Popen(["nwg-displays"])
            
            # Wait a bit for window to appear
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                self.log_message("nwg-displays is running. Please configure your displays.")
                self.log_message("Close the nwg-displays window when done to continue.")
                
                # Wait for process to complete
                process.wait()
                self.log_message("nwg-displays closed. Display configuration saved.")
            else:
                self.log_message("nwg-displays exited immediately. It may not be installed or configured.")
            
            return True
        except Exception as e:
            self.log_message(f"Failed to launch nwg-displays: {str(e)}", is_error=True)
            self.log_message("You can configure displays manually later.")
            return True  # Continue anyway
    
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
            "Close the nwg-displays window when you're done to continue.\n\n"
            "If nwg-displays doesn't open, you may need to install it first."
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
            try:
                shutil.rmtree(tmp_dir)
                self.log_message("Cleaned up temporary files")
            except Exception as e:
                self.log_message(f"Failed to clean tmp dir: {e}", is_error=True)
        
        return True
    
    def start_swww(self):
        """Start swww wallpaper daemon"""
        self.log_message("Starting swww...")
        
        # Start swww daemon
        cmd = "swww-daemon 2>/dev/null &"
        self.run_user_command(cmd, "Start swww daemon")
        
        # Run swww script if it exists
        scripts_dir = self.home_dir / "scripts"
        swww_script = scripts_dir / "swww.sh"
        if swww_script.exists():
            cmd = f"bash {swww_script} &"
            self.run_user_command(cmd, "Run swww script")
        else:
            self.log_message("swww.sh not found, skipping")
        
        return True
    
    def setup_pywal(self):
        """Setup pywal"""
        self.log_message("Setting up pywal...")
        
        # Check if pywal is installed
        pywal_check = subprocess.run(["which", "wal"], capture_output=True)
        if pywal_check.returncode != 0:
            self.log_message("pywal not installed, skipping pywal setup")
            return True
        
        # Apply pywal theme
        theme_file = self.home_dir / ".config" / "pywal" / "themes" / "active.json"
        if theme_file.exists():
            cmd = f"wal --theme {theme_file}"
            if not self.run_user_command(cmd, "Apply pywal theme"):
                self.log_message("Warning: Failed to apply pywal theme", is_error=True)
        
        # Copy pywal config to Kvantum
        wal_cache = self.home_dir / ".cache" / "wal"
        
        kvantum_config = wal_cache / "pywal.kvconfig"
        kvantum_dest = self.home_dir / ".config" / "Kvantum" / "pywal" / "pywal.kvconfig"
        if kvantum_config.exists():
            kvantum_dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(kvantum_config, kvantum_dest)
                self.log_message("Copied pywal kvantum config")
            except Exception as e:
                self.log_message(f"Failed to copy kvantum config: {e}", is_error=True)
        
        kvantum_svg = wal_cache / "pywal.svg"
        kvantum_svg_dest = self.home_dir / ".config" / "Kvantum" / "pywal" / "pywal.svg"
        if kvantum_svg.exists():
            try:
                shutil.copy2(kvantum_svg, kvantum_svg_dest)
                self.log_message("Copied pywal svg")
            except Exception as e:
                self.log_message(f"Failed to copy pywal svg: {e}", is_error=True)
        
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
            ]
            
            self.total_steps = len(steps)
            
            for i, (step_func, description) in enumerate(steps, 1):
                self.update_progress(i, self.total_steps, description)
                self.log_message(f"Step {i}/{self.total_steps}: {description}")
                
                if not step_func():
                    self.log_message(f"Warning: Step '{description}' had issues, continuing...", is_error=True)
                else:
                    self.log_message(f"Step '{description}' completed successfully")
                
                # Small delay between steps
                time.sleep(1)
            
            # Launch nwg-displays at the end
            self.update_progress(self.total_steps + 1, self.total_steps + 2, "Launching nwg-displays")
            self.launch_nwg_displays()
            
            self.update_progress(self.total_steps + 2, self.total_steps + 2, "Installation complete!")
            self.log_message("✅ Installation complete!")
            self.log_message("\nNext steps:")
            self.log_message("1. Log out and log back in to apply all changes")
            self.log_message("2. Run ~/dots/reboot.sh for final configuration (optional)")
            self.log_message("3. Configure any remaining settings manually")
            
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
        dialog.format_secondary_text(f"Error: {message}\n\nCheck the log for details.")
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
            "A log out/in or reboot is recommended to apply all changes.\n"
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
        
        # Show warning dialog
        dialog = Gtk.MessageDialog(
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Start Installation"
        )
        dialog.format_secondary_text(
            "This will install packages and configure your system.\n\n"
            "You may be prompted for your password multiple times.\n"
            "The installation may take 30+ minutes depending on your internet speed.\n\n"
            "Do you want to continue?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response != Gtk.ResponseType.OK:
            return
        
        # Start installation in separate thread
        self.install_thread = threading.Thread(target=self.run_installation)
        self.install_thread.daemon = True
        self.install_thread.start()
    
    def create_ui(self):
        """Create the main UI"""
        # Create main window
        self.window = Gtk.Window(title="Dotfiles Installer")
        self.window.set_default_size(900, 700)
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
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.pack_start(header_box, False, False, 0)
        
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold'>Dotfiles Installer</span>")
        title_label.set_halign(Gtk.Align.START)
        header_box.pack_start(title_label, False, False, 0)
        
        subtitle_label = Gtk.Label("Install and configure dotfiles from ~/dots")
        subtitle_label.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle_label, False, False, 0)
        
        # Separator
        main_box.pack_start(Gtk.Separator(), False, False, 5)
        
        # Progress section
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.pack_start(progress_box, False, False, 0)
        
        self.status_label = Gtk.Label("Ready to install")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_bottom(5)
        progress_box.pack_start(self.status_label, False, False, 0)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_pulse_step(0.1)
        progress_box.pack_start(self.progress_bar, False, False, 0)
        
        # Log view
        log_frame = Gtk.Frame(label="Installation Log")
        log_frame.set_margin_top(10)
        main_box.pack_start(log_frame, True, True, 0)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(400)
        log_frame.add(scrolled_window)
        
        self.log_textview = Gtk.TextView()
        self.log_textview.set_editable(False)
        self.log_textview.set_monospace(True)
        self.log_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        # Set font
        font_desc = Pango.FontDescription("Monospace 10")
        self.log_textview.override_font(font_desc)
        
        scrolled_window.add(self.log_textview)
        
        self.log_buffer = self.log_textview.get_buffer()
        
        # Create tags
        self.log_buffer.create_tag("error", foreground="red", weight=Pango.Weight.BOLD)
        self.log_buffer.create_tag("warning", foreground="orange")
        self.log_buffer.create_tag("success", foreground="green")
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(10)
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
        
        # Status bar
        status_bar = Gtk.Statusbar()
        status_bar.push(0, "Ready - Make sure your dotfiles are in ~/dots/")
        main_box.pack_start(status_bar, False, False, 0)
        
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
        print("It will use pkexec for privileged operations when needed.")
        sys.exit(1)
    
    # Check if dots directory exists
    dots_dir = Path.home() / "dots"
    if not dots_dir.exists():
        print(f"Error: dots directory not found at {dots_dir}")
        print("Please clone your dotfiles to ~/dots first.")
        
        # Ask user if they want to create it
        response = input("Create empty ~/dots directory? (y/N): ")
        if response.lower() == 'y':
            dots_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created {dots_dir}")
            print("Please add your dotfiles to this directory and run the installer again.")
        sys.exit(1)
    
    # Start the installer
    app = DotfilesInstaller()
    app.run()


if __name__ == "__main__":
    main()
