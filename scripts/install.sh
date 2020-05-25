#! /bin/bash

cd /home/vibflysleep/VIBFlySleep/LeMDT
INSTALLED=$(python -m pip list | grep pypylon | wc -l)
if [ $INSTALLED -eq 0 ]
then
  rm wheels/pypylon*.whl
  wget  https://github.com/basler/pypylon/releases/download/1.4.0/pypylon-1.4.0-cp37-cp37m-linux_x86_64.whl
  mv pypylon*.whl wheels/
  python -m pip install wheels/pypylon*whl
fi

INSTALLED=$(python -m pip list | grep anaconda3 | grep LeMDT | wc -l)
if [ $INSTALLED -eq 1 ]
then
 echo 'Found previous installation of LeMDT. Uninstalling now'
 python -m pip uninstall -y LeMDT
fi

python -m pip install wheels/LeMDT*.whl


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

 
echo "Exec=sudo bash -c 'LD_LIBRARY_PATH=$PYTHON_DIR/../lib/ $PYTHON_EXECUTABLE -q -X faulthandler -m LeMDT --track --camera pylon --arduino'" >> learningmemorysetup.desktop
echo "Icon=$DIR/LeMDT/static/fly.png" >> learningmemorysetup.desktop
chmod +x learningmemorysetup.desktop

ln -f learningmemorysetup.desktop ~/.local/share/applications
dconf write /org/gnome/shell/favorite-apps "`dconf read /org/gnome/shell/favorite-apps | sed 's/]/, '\''learningmemorysetup.desktop'\'']/'`"

#echo 'export LD_LIBRARY_PATH=~/anaconda3/envs/py37/lib/' >> ~/.bashrc
