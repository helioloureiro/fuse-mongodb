#! /bin/bash

TARGETDIR=./mnt

updir=$(readlink -f $TARGETDIR/..)

alert() {
 echo $@
 logger fuse-mongodb-testing "$@"
}

alert "Mounting $TARGETDIR using fuse-mongodb."
python3 -u ./fuse-mongodb.py $TARGETDIR
response=$?
if [[ $response -ne 0 ]]; then
    alert "Fuse failed.  Stopping test."
    exit $response
fi
sleep 1
alert "Listing parent directory."
ls -al $updir
sleep 1
alert "Listing directory."
ls -al $TARGETDIR
sleep 1
if [ $? -eq 0 ]; then
    alert "Changing directory to $TARGETDIR"
    cd $TARGETDIR
    sleep 1
    last_file=$(ls -tr | grep -v mongodb | head -1)
    alert "Getting file content: $last_file"
    cat $last_file | head
    sleep 1
    random_file="$USER-testing-$RANDOM"
    alert "Testing write: $random_file"
    touch $random_file
    sleep 1
    cd -
fi
alert "umounting $TARGETDIR"
sudo umount $TARGETDIR


