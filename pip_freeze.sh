#!/bin/sh

echo "writing python dependencies to 'requirements.txt"

sudo pip3 freeze --local >requirements.txt

# force reinstall of dependencies from file:
#sudo pip3 install --upgrade --force-reinstall -r requirements.txt

echo "complete."

