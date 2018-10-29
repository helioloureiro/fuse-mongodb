#! /bin/bash

DESTDIR=/mnt/mongodb
echo "building"
make clean all
if [ $? -ne 0 ];  then
    echo "Building broken"
    exit 1
fi
echo "mouting $DESTDIR using fuse-mongodb"
if [ ! -d $DESTDIR ]; then
    sudo mkdir -p $DESTDIR
fi
updir=$(readlink -f $DESTDIR/..)
sudo ./fuse-mongodb $DESTDIR
echo "listing directory above"
ls -al $updir
echo "listing directory itself"
ls -al $DESTDIR
echo "umounting $DESTDIR"
sudo umount $DESTDIR


