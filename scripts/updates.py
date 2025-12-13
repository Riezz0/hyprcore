#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Polkit', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, Polkit
import subprocess
import threading
import os
import sys

class UpdateManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="Update Manager")
        self.set_default_size(800, 600)
        self.set_border_width(10)
        
        # Initialize Polkit authority
        self.polkit_authority = None
        try:
            self.polkit_authority = Polkit.Authority.get_sync(None)
        except:
            print("Warning: Could not initialize Polkit authority")
        
        # Colors for status
        self.colors = {
            "success": "#4CAF50",
            "error": "#F44336",
            "warning": "#FF9800",
            "info": "#2196F3",
            "updating": "#9C27B0"
        }
        
        # Store for updates
        self.updates = {
            "flatpak": {"available": [], "selected": [], "count": 0},
            "pacman": {"available": [], "selected": [], "count": 0},
            "yay": {"available": [], "selected": [], "count": 0}
        }
        
        # UI elements storage
        self.ui_elements = {
            "flatpak": {"listbox": None, "count_label": None},
            "pacman": {"listbox": None, "count_label": None},
            "yay": {"listbox": None, "count_label": None}
        }
        
        self.create_ui()
        self.check_updates()
    
    def create_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label="<span size='x-large' weight='bold'>System Update Manager</span>")
        title.set_use_markup(True)
        header.pack_start(title, False, False, 0)
        
        # Refresh button
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        header.pack_end(refresh_btn, False, False, 0)
        
        main_box.pack_start(header, False, False, 0)
        
        # Status bar
        self.status_bar = Gtk.Statusbar()
        self.status_context = self.status_bar.get_context_id("updates")
        main_box.pack_start(self.status_bar, False, False, 0)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        main_box.pack_start(self.progress_bar, False, False, 0)
        
        # Create notebook for different package managers
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        
        # Flatpak tab
        flatpak_box = self.create_package_tab("flatpak", "Flatpak Updates")
        notebook.append_page(flatpak_box, Gtk.Label(label="Flatpak"))
        
        # Pacman tab
        pacman_box = self.create_package_tab("pacman", "Pacman Updates")
        notebook.append_page(pacman_box, Gtk.Label(label="Pacman"))
        
        # AUR/YAY tab
        aur_box = self.create_package_tab("yay", "AUR Updates")
        notebook.append_page(aur_box, Gtk.Label(label="AUR (YAY)"))
        
        # Update Log tab
        log_box = self.create_log_tab()
        notebook.append_page(log_box, Gtk.Label(label="Update Log"))
        
        main_box.pack_start(notebook, True, True, 0)
        
        # Control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_homogeneous(True)
        
        self.update_all_btn = Gtk.Button(label="Update All")
        self.update_all_btn.connect("clicked", self.on_update_all_clicked)
        self.update_all_btn.set_sensitive(False)
        
        self.update_selected_btn = Gtk.Button(label="Update Selected")
        self.update_selected_btn.connect("clicked", self.on_update_selected_clicked)
        self.update_selected_btn.set_sensitive(False)
        
        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda x: Gtk.main_quit())
        
        button_box.pack_start(self.update_all_btn, True, True, 0)
        button_box.pack_start(self.update_selected_btn, True, True, 0)
        button_box.pack_start(close_btn, True, True, 0)
        
        main_box.pack_start(button_box, False, False, 0)
        
        self.add(main_box)
    
    def create_package_tab(self, pkg_type, title_text):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Title
        title = Gtk.Label(label=f"<b>{title_text}</b>")
        title.set_use_markup(True)
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)
        
        # Count label
        count_label = Gtk.Label()
        count_label.set_halign(Gtk.Align.START)
        box.pack_start(count_label, False, False, 0)
        self.ui_elements[pkg_type]["count_label"] = count_label
        
        # Scrollable list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(300)
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(listbox)
        
        box.pack_start(scrolled, True, True, 0)
        self.ui_elements[pkg_type]["listbox"] = listbox
        
        # Select all button for this tab
        select_btn = Gtk.Button(label=f"Select All {pkg_type.capitalize()} Updates")
        select_btn.connect("clicked", self.on_select_all_clicked, pkg_type)
        box.pack_start(select_btn, False, False, 0)
        
        return box
    
    def create_log_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Text view for logs
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        # Create tag for colors
        text_buffer = self.log_view.get_buffer()
        for name, color in self.colors.items():
            text_buffer.create_tag(name, foreground=color)
        
        scrolled.add(self.log_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Clear log button
        clear_btn = Gtk.Button(label="Clear Log")
        clear_btn.connect("clicked", self.on_clear_log_clicked)
        box.pack_start(clear_btn, False, False, 0)
        
        return box
    
    def add_log(self, message, color_tag="info"):
        GLib.idle_add(self._add_log_idle, message, color_tag)
    
    def _add_log_idle(self, message, color_tag):
        text_buffer = self.log_view.get_buffer()
        end_iter = text_buffer.get_end_iter()
        
        timestamp = GLib.DateTime.new_now_local().format("%H:%M:%S")
        text_buffer.insert_with_tags_by_name(end_iter, f"[{timestamp}] ", "info")
        text_buffer.insert_with_tags_by_name(end_iter, f"{message}\n", color_tag)
        
        # Scroll to end
        mark = text_buffer.get_insert()
        text_buffer.place_cursor(text_buffer.get_end_iter())
        self.log_view.scroll_mark_onscreen(mark)
        
        # Update status bar
        self.status_bar.push(self.status_context, message)
    
    def check_updates(self):
        self.add_log("Checking for updates...", "info")
        self.progress_bar.set_fraction(0.33)
        self.progress_bar.set_text("Checking Flatpak updates...")
        
        # Check Flatpak updates
        threading.Thread(target=self.check_flatpak_updates, daemon=True).start()
    
    def check_flatpak_updates(self):
        try:
            result = subprocess.run(
                ["flatpak", "remote-ls", "--updates", "--columns=application,version,origin"],
                capture_output=True,
                text=True,
                check=False
            )
            
            updates = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        updates.append({
                            "name": parts[0],
                            "version": parts[1],
                            "origin": parts[2]
                        })
            
            GLib.idle_add(self.update_ui_with_updates, "flatpak", updates)
            
            # Check Pacman updates
            self.progress_bar.set_fraction(0.66)
            self.progress_bar.set_text("Checking Pacman updates...")
            threading.Thread(target=self.check_pacman_updates, daemon=True).start()
            
        except Exception as e:
            self.add_log(f"Error checking Flatpak updates: {e}", "error")
    
    def check_pacman_updates(self):
        try:
            result = subprocess.run(
                ["checkupdates"],
                capture_output=True,
                text=True,
                check=False
            )
            
            updates = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    # checkupdates format: "package-name current-version -> new-version"
                    parts = line.split()
                    if len(parts) >= 4:
                        updates.append({
                            "name": parts[0],
                            "old_version": parts[1],
                            "new_version": parts[3]
                        })
            
            GLib.idle_add(self.update_ui_with_updates, "pacman", updates)
            
            # Check AUR updates
            self.progress_bar.set_fraction(0.9)
            self.progress_bar.set_text("Checking AUR updates...")
            threading.Thread(target=self.check_aur_updates, daemon=True).start()
            
        except subprocess.CalledProcessError as e:
            # checkupdates returns non-zero exit code when no updates are available
            if e.returncode == 2:  # No updates available
                GLib.idle_add(self.update_ui_with_updates, "pacman", [])
            else:
                self.add_log(f"Error checking Pacman updates: {e.stderr}", "error")
        except Exception as e:
            self.add_log(f"Error checking Pacman updates: {e}", "error")
    
    def check_aur_updates(self):
        try:
            result = subprocess.run(
                ["yay", "-Qua"],
                capture_output=True,
                text=True,
                check=False
            )
            
            updates = []
            for line in result.stdout.strip().split('\n'):
                if line and "aur/" in line:
                    # Parse yay output
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[0].replace('aur/', '')
                        updates.append({
                            "name": name,
                            "old_version": parts[1],
                            "new_version": parts[3].strip()
                        })
            
            GLib.idle_add(self.update_ui_with_updates, "yay", updates)
            GLib.idle_add(self.finish_update_check)
            
        except Exception as e:
            self.add_log(f"Error checking AUR updates: {e}", "error")
            GLib.idle_add(self.finish_update_check)
    
    def update_ui_with_updates(self, pkg_type, updates):
        self.updates[pkg_type]["available"] = updates
        self.updates[pkg_type]["count"] = len(updates)
        
        listbox = self.ui_elements[pkg_type]["listbox"]
        count_label = self.ui_elements[pkg_type]["count_label"]
        
        # Clear existing rows
        for row in listbox.get_children():
            listbox.remove(row)
        
        # Add update rows
        for update in updates:
            row = self.create_update_row(pkg_type, update)
            listbox.add(row)
        
        # Update count label
        count_text = f"Found {len(updates)} updates"
        if pkg_type == "yay":
            count_text += " (AUR)"
        count_label.set_text(count_text)
        count_label.set_markup(f"<span foreground='{self.colors['info']}'>{count_text}</span>")
        
        # Show listbox if updates exist
        listbox.show_all()
        
        self.add_log(f"Found {len(updates)} {pkg_type} updates", "info")
    
    def finish_update_check(self):
        total_updates = sum(self.updates[t]["count"] for t in ["flatpak", "pacman", "yay"])
        
        if total_updates > 0:
            self.update_all_btn.set_sensitive(True)
            self.update_selected_btn.set_sensitive(True)
            self.add_log(f"Update check complete. Found {total_updates} total updates.", "success")
        else:
            self.add_log("System is up to date!", "success")
        
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("Ready")
    
    def create_update_row(self, pkg_type, update):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(5)
        row.set_margin_bottom(5)
        
        # Checkbox
        check = Gtk.CheckButton()
        check.connect("toggled", self.on_update_toggled, pkg_type, update["name"])
        row.pack_start(check, False, False, 0)
        
        # Package name
        name_label = Gtk.Label(label=f"<b>{update['name']}</b>")
        name_label.set_use_markup(True)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_hexpand(True)
        row.pack_start(name_label, True, True, 0)
        
        # Version info
        if pkg_type == "flatpak":
            version_text = f"{update['version']} ({update['origin']})"
        else:
            version_text = f"{update['old_version']} → {update['new_version']}"
        
        version_label = Gtk.Label(label=version_text)
        version_label.set_halign(Gtk.Align.END)
        row.pack_start(version_label, False, False, 0)
        
        return row
    
    def on_update_toggled(self, checkbutton, pkg_type, package_name):
        if checkbutton.get_active():
            self.updates[pkg_type]["selected"].append(package_name)
        else:
            if package_name in self.updates[pkg_type]["selected"]:
                self.updates[pkg_type]["selected"].remove(package_name)
    
    def on_select_all_clicked(self, button, pkg_type):
        listbox = self.ui_elements[pkg_type]["listbox"]
        for row in listbox.get_children():
            checkbox = row.get_children()[0]  # First child is the checkbox
            checkbox.set_active(True)
    
    def on_refresh_clicked(self, button):
        self.add_log("Refreshing update list...", "info")
        # Clear existing updates
        for pkg_type in ["flatpak", "pacman", "yay"]:
            self.updates[pkg_type] = {"available": [], "selected": [], "count": 0}
            listbox = self.ui_elements[pkg_type]["listbox"]
            for row in listbox.get_children():
                listbox.remove(row)
            self.ui_elements[pkg_type]["count_label"].set_text("")
        
        self.update_all_btn.set_sensitive(False)
        self.update_selected_btn.set_sensitive(False)
        self.check_updates()
    
    def on_update_all_clicked(self, button):
        self.add_log("Starting update of all packages...", "updating")
        
        # Select all updates
        for pkg_type in ["flatpak", "pacman", "yay"]:
            self.updates[pkg_type]["selected"] = [update["name"] for update in self.updates[pkg_type]["available"]]
        
        self.perform_updates()
    
    def on_update_selected_clicked(self, button):
        self.add_log("Starting update of selected packages...", "updating")
        self.perform_updates()
    
    def perform_updates(self):
        # Disable buttons during update
        self.update_all_btn.set_sensitive(False)
        self.update_selected_btn.set_sensitive(False)
        
        # Start update process
        threading.Thread(target=self.run_updates, daemon=True).start()
    
    def run_updates(self):
        # Update Flatpaks
        flatpak_selected = self.updates["flatpak"]["selected"]
        if flatpak_selected:
            GLib.idle_add(self.progress_bar.set_fraction, 0.2)
            GLib.idle_add(self.progress_bar.set_text, f"Updating {len(flatpak_selected)} Flatpak(s)")
            
            try:
                cmd = ["flatpak", "update", "-y"] + flatpak_selected
                self.add_log(f"Running: {' '.join(cmd)}", "updating")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    self.add_log(f"Successfully updated {len(flatpak_selected)} Flatpaks", "success")
                else:
                    self.add_log(f"Failed to update Flatpaks: {result.stderr}", "error")
            except Exception as e:
                self.add_log(f"Error updating Flatpak: {e}", "error")
        
        # Update Pacman packages
        pacman_selected = self.updates["pacman"]["selected"]
        if pacman_selected:
            GLib.idle_add(self.progress_bar.set_fraction, 0.5)
            GLib.idle_add(self.progress_bar.set_text, f"Updating {len(pacman_selected)} Pacman package(s)")
            
            # Use pkexec for pacman
            try:
                self.add_log("Requesting sudo permissions for Pacman updates...", "info")
                
                # Use pkexec for polkit authentication
                cmd = ["pkexec", "pacman", "-Syu", "--noconfirm"] + pacman_selected
                self.add_log(f"Running: {' '.join(cmd)}", "updating")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    self.add_log("Successfully updated Pacman packages", "success")
                else:
                    self.add_log(f"Failed to update Pacman packages: {result.stderr}", "error")
                    
            except Exception as e:
                self.add_log(f"Error updating Pacman packages: {e}", "error")
        
        # Update AUR packages (yay doesn't need sudo)
        aur_selected = self.updates["yay"]["selected"]
        if aur_selected:
            GLib.idle_add(self.progress_bar.set_fraction, 0.8)
            GLib.idle_add(self.progress_bar.set_text, f"Updating {len(aur_selected)} AUR package(s)")
            
            try:
                cmd = ["yay", "-S", "--noconfirm"] + aur_selected
                self.add_log(f"Running: {' '.join(cmd)}", "updating")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    self.add_log(f"Successfully updated {len(aur_selected)} AUR packages", "success")
                else:
                    self.add_log(f"Failed to update AUR packages: {result.stderr}", "error")
            except Exception as e:
                self.add_log(f"Error updating AUR packages: {e}", "error")
        
        # Finalize
        GLib.idle_add(self.progress_bar.set_fraction, 1.0)
        GLib.idle_add(self.progress_bar.set_text, "Update complete!")
        self.add_log("All updates completed!", "success")
        
        # Re-enable buttons
        GLib.idle_add(self.update_all_btn.set_sensitive, True)
        GLib.idle_add(self.update_selected_btn.set_sensitive, True)
        
        # Refresh update list after 2 seconds
        GLib.timeout_add_seconds(2, self.on_refresh_clicked, None)
    
    def on_clear_log_clicked(self, button):
        text_buffer = self.log_view.get_buffer()
        text_buffer.set_text("")

def main():
    # Check for required commands
    required_commands = ["flatpak", "checkupdates", "yay", "pkexec"]
    missing = []
    
    for cmd in required_commands:
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
        except:
            missing.append(cmd)
    
    if missing:
        print(f"Missing required commands: {', '.join(missing)}")
        print("Note: 'checkupdates' is part of the 'pacman-contrib' package")
        print("Install with: sudo pacman -S pacman-contrib")
        return
    
    win = UpdateManager()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
