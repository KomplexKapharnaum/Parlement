#!/bin/bash

BASEPATH="$(dirname "$(readlink -f "$0")")"
DISTRO=''

echo "$BASEPATH"
cd "$BASEPATH"

ln -sf "$BASEPATH/parlement" /usr/local/bin/
ln -sf "$BASEPATH/parlement.service" /etc/systemd/system/
systemctl daemon-reload

FILE=/boot/starter.txt
if test -f "$FILE"; then
echo "## [Parlement] burgerquizz server
# parlement
" >> /boot/starter.txt
fi


echo "Parlement INSTALLED"
