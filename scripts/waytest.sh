#!/bin/bash

killall waybar
waybar -c ~/.config/waybar/main-bar/bar-config.jsonc -s ~/.config/waybar/main-bar/bar-style.css 
