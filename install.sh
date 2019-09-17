#! /bin/bash


INSTALLED=$(python3 -m pip list | grep pypylon | wc -l)
if [ $INSTALLED -eq 0 ]
then
  rm pypylon*.whl
  wget https://github.com/basler/pypylon/releases/download/1.4.0/pypylon-1.4.0-cp37-cp37m-linux_x86_64.whl
  python3 -m pip install pypylon*whl
fi

INSTALLED=$(python3 -m pip list | grep LeMDT | wc -l)
if [ $INSTALLED -eq 1 ]
then
 echo 'Found previous installation of LeMDT. Uninstalling now'
 python3 -m pip uninstall -y LeMDT
fi

python3 -m pip install LeMDT*.whl


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_EXECUTABLE=`which python3`
PYTHON_DIR=$(dirname `which python3`)
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
