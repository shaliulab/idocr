#! /bin/bash

sudo cp LeMDT.desktop /usr/share/applications/
dconf write /org/gnome/shell/favorite-apps "`dconf read /org/gnome/shell/favorite-apps | sed 's/]/, '\''LeMDT.desktop'\'']/'`"
