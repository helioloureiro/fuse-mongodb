#! /bin/bash

echo "building"
make clean all
if [ $? -ne 0 ];  then
    echo "Building broken"
    exit 1
fi
echo "mouting /mnt/mongodb using fuse-mongodb"
sudo -E env LD_LIBRARY_PATH=../libfuse/build/lib ./fuse-mongodb /mnt/mongodb
echo "listing directory"
ls -al /mnt
ls -al /mnt/mongodb
echo "umounting /mnt/mongodb"
sudo umount /mnt/mongodb


