#! /bin/bash


INSTALLED=$(pip list | grep pypylon | wc -l)
if [ $INSTALLED -eq 0 ]
then
  rm pypylon*.whl
  https://github.com/basler/pypylon/releases/download/1.4.0/pypylon-1.4.0-cp37-cp37m-linux_x86_64.whl
  pip install pypylon*whl
fi

INSTALLED=$(pip list | grep LeMDT | wc -l)
if [ $INSTALLED -eq 1 ]
then
 echo 'Found previous installation of LeMDT. Uninstalling now'
 pip uninstall -y LeMDT
fi

pip install LeMDT*.whl


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_EXECUTABLE=`which python`
PYTHON_DIR=$(dirname `which python`)
cd $DIR
printf '#!/usr/bin/env xdg-open
[Desktop Entry]
Name=learningmemorysetup
Type=Application
Terminal=true
Categories=GTK;GNOME;Utility;
' > learningmemorysetup.desktop

 
echo "Exec=bash -c 'LD_LIBRARY_PATH=$PYTHON_DIR/../lib/ $PYTHON_EXECUTABLE -m LeMDT --track --camera pylon --arduino'" >> learningmemorysetup.desktop
echo "Icon=$DIR/LeMDT/static/fly.png" >> learningmemorysetup.desktop
chmod +x learningmemorysetup.desktop

ln -f learningmemorysetup.desktop ~/.local/share/applications
dconf write /org/gnome/shell/favorite-apps "`dconf read /org/gnome/shell/favorite-apps | sed 's/]/, '\''learningmemorysetup.desktop'\'']/'`"
