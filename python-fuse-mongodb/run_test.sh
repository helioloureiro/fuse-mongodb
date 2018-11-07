#! /bin/bash

TARGETDIR=./mnt

updir=$(readlink -f $TARGETDIR/..)

alert() {
 echo $@
 logger fuse-mongodb-testing "$@"
}

alert "Mounting $TARGETDIR using fuse-mongodb."
python3 ./fuse-mongodb.py $TARGETDIR

alert "Listing parent directory."
ls -al $updir
alert "Listing directory."
ls -al $TARGETDIR
if [ $? -eq 0 ]; then
    last_file=$(ls -tr $TARGETDIR | grep -v mongodb | head -1)
    alert "Getting file content: $TARGETDIR/$last_file"
    cat $TARGETDIR/$last_file | head
    random_file="$USER-testing-$RANDOM"
    alert "Testing write: $random_file"
    touch $TARGETDIR/$random_file
fi
sleep 1
alert "umounting $TARGETDIR"
sudo umount $TARGETDIR


