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
sudo whoami > /dev/null 2>&1 #warm up
sudo ./fuse-mongodb $DESTDIR &
sleep 1
echo "listing directory above"
ls -al $updir
echo "listing directory itself"
ls -al $DESTDIR
echo "listing directory above as ROOT"
sudo ls -al $updir
echo "listing directory itself as ROOT"
sudo ls -al $DESTDIR
sleep 1
kill -TERM %1
echo "umounting $DESTDIR"
sudo umount $DESTDIR


