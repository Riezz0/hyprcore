#!/bin/bash

yay -S --needed --noconfirm \
    swww qt5-quickcontrols qt5-quickcontrols2 qt5-graphicaleffects \
    hypridle hyprlock hyprpicker tree qt5ct qt6ct qt5-styleplugins \
    wl-clipboard firefox code nemo vlc nwg-look gnome-disk-utility \
    nwg-displays zsh ttf-meslo-nerd ttf-font-awesome ttf-font-awesome-4 \
    ttf-font-awesome-5 waybar rust cargo fastfetch cmatrix pavucontrol \
    net-tools python-pip python-psutil python-virtualenv python-requests \
    python-hijri-converter python-pytz python-gobject xfce4-settings \
    xfce-polkit exa libreoffice-fresh rofi-wayland neovim goverlay-git \
    flatpak python-pywal16 python-pywalfox make linux-firmware dkms \
    automake linux-zen-headers kvantum-qt5 chromium nemo-fileroller\

mkdir -p ~/git ~/venv /home/$USER/tmp/
sudo mkdir -p /etc/modules-load.d/

mkdir -p ~/.local/share/fonts
cp -r /home/$USER/dots/fonts/* /home/$USER/.local/share/fonts
fc-cache -fv

git clone "https://github.com/zsh-users/zsh-autosuggestions.git" "/home/$USER/dots/tmp/zsh-autosuggestions/"
git clone "https://github.com/zsh-users/zsh-syntax-highlighting.git" "/home/$USER/dots/tmp/zsh-syntax-highlighting/"
git clone "https://github.com/zdharma-continuum/fast-syntax-highlighting.git" "/home/$USER/dots/tmp/fast-syntax-highlighting/"
git clone --depth 1 -- "https://github.com/marlonrichert/zsh-autocomplete.git" "/home/$USER/dots/tmp/zsh-autocomplete/"
git clone "https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv.git" "/home/$USER/dots/tmp/autoswitch_virtualenv/"

RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
chsh -s $(which zsh)

cp -r /home/$USER/dots/tmp/autoswitch_virtualenv/ ~/.oh-my-zsh/custom/plugins/
cp -r /home/$USER/dots/tmp/fast-syntax-highlighting/ ~/.oh-my-zsh/custom/plugins/
cp -r /home/$USER/dots/tmp/zsh-autocomplete/ ~/.oh-my-zsh/custom/plugins/
cp -r /home/$USER/dots/tmp/zsh-autosuggestions/ ~/.oh-my-zsh/custom/plugins/
cp -r /home/$USER/dots/tmp/zsh-syntax-highlighting/ ~/.oh-my-zsh/custom/plugins/

git clone https://github.com/Fred78290/nct6687d /home/$USER/tmp/nct6687d
cd /home/$USER/tmp/nct6687d/
make dkms/install
sudo cp -r /home/$USER/dots/sys/no_nct6683.conf /etc/modprobe.d/
sudo cp -r /home/$USER/dots/sys/nct6687.conf /etc/modules-load.d/nct6687.conf
sudo modprobe nct6687

rm -rf /home/$USER/dots/tmp/
rm -rf /home/$USER/.config/hypr
rm -rf /home/$USER/.config/kitty
sudo rm /etc/sddm.conf
sudo rm /etc/default/grub
rm -rf ~/.zshrc

ln -s /home/$USER/dots/.zshrc /home/$USER/
ln -s /home/$USER/dots/fastfetch/ /home/$USER/.config/
ln -s /home/$USER/dots/hypr/ /home/$USER/.config/
ln -s /home/$USER/dots/kitty /home/$USER/.config/
ln -s /home/$USER/dots/Kvantum/ /home/$USER/.config/
ln -s /home/$USER/dots/nvim/ /home/$USER/.config/
ln -s /home/$USER/dots/pywal/ /home/$USER/.config/
ln -s /home/$USER/dots/qt5ct/ /home/$USER/.config/
ln -s /home/$USER/dots/qt6ct/ /home/$USER/.config/
ln -s /home/$USER/dots/rofi/ /home/$USER/.config/
ln -s /home/$USER/dots/scripts/ /home/$USER/.config/
ln -s /home/$USER/dots/wal/ /home/$USER/.config/
ln -s /home/$USER/dots/wallpapers/ /home/$USER/.config/
ln -s /home/$USER/dots/waybar/ /home/$USER/.config/
ln -s /home/$USER/dots/xdg-desktop-portal/ /home/$USER/.config/
ln -s /home/$USER/dots/.icons/ /home/$USER/
ln -s /home/$USER/dots/.themes/ /home/$USER/
ln -s /home/$USER/dots/dunst/ /home/$USER/.config/

sudo rm -rf /usr/share/icons/default
sudo cp -r /home/$USER/dots/sys/cursors/default /usr/share/icons/
sudo cp -r /home/$USER/dots/sys/cursors/oreo_white_cursors /usr/share/icons/

gsettings set org.gnome.desktop.interface cursor-theme "oreo_white_cursors"
gsettings set org.gnome.desktop.interface icon-theme "oomox-Tokyo-Night"
gsettings set org.gnome.desktop.interface gtk-theme "oomox-Tokyo-Night"
gsettings set org.gnome.desktop.interface font-name "MesloLGL Nerd Font 12"
gsettings set org.gnome.desktop.interface document-font-name "MesloLGL Nerd Font 12"
gsettings set org.gnome.desktop.interface monospace-font-name "MesloLGL Mono Nerd Font 12"
gsettings set org.gnome.desktop.wm.preferences titlebar-font "MesloLGL Mono Nerd Font 12"

swww-daemon 2>/dev/null &
bash /home/$USER/scripts/swww.sh &
wal --theme ~/.config/pywal/themes/active.json

cp "${HOME}"/.cache/wal/pywal.kvconfig "${HOME}"/.config/Kvantum/pywal/pywal.kvconfig
cp "${HOME}"/.cache/wal/pywal.svg "${HOME}"/.config/Kvantum/pywal/pywal.svg

sudo cp -r /home/$USER/dots/sys/sddm/sddm.conf /etc/
sudo cp -r /home/$USER/dots/sys/sddm/tokyo-night/ /usr/share/sddm/themes/

sudo cp -r /home/$USER/dots/sys/grub/grub /etc/default/
sudo cp -r /home/$USER/dots/sys/grub/tokyo-night /usr/share/grub/themes/
sudo grub-mkconfig -o /boot/grub/grub.cfg

bash /home/$USER/dots/reboot.sh

#sudo systemctl enable coolercontrold.service
#sudo systemctl start coolercontrold.service
