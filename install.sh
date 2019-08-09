#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR
echo "Exec=bash -c 'cd $DIR/.. && python -m LeMDT --track --camera pylon --arduino'" >> LeMDT.desktop
echo "Icon=$DIR/static/fly.png" >> LeMDT.desktop

sudo cp LeMDT.desktop /usr/share/applications/
dconf write /org/gnome/shell/favorite-apps "`dconf read /org/gnome/shell/favorite-apps | sed 's/]/, '\''LeMDT.desktop'\'']/'`"
