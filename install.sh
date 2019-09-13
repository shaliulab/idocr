#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_EXECUTABLE=$1
cd $DIR
echo "Exec=bash -c 'cd $DIR/.. && $PYTHON_EXECUTABLE -m LeMDT --track --camera pylon --arduino'" >> learningmemorysetup.desktop
echo "Icon=$DIR/static/fly.png" >> learningmemorysetup.desktop

cp learningmemorysetup.desktop ~/.local/share/applications
dconf write /org/gnome/shell/favorite-apps "`dconf read /org/gnome/shell/favorite-apps | sed 's/]/, '\''learningmemorysetup.desktop'\'']/'`"
