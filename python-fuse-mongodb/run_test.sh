#! /bin/bash

TARGETDIR=./mnt

updir=$(readlink -f $TARGETDIR/..)

echo "mounting $TARGETDIR using fuse-mongodb"
python3 ./fuse-mongodb.py $TARGETDIR

echo "listing parent directory"
ls -al $updir
echo "listing directory"
ls -al $TARGETDIR
echo "umounting $TARGETDIR"
sudo umount $TARGETDIR


