#!/bin/bash -eu

DIR=`pwd`/src/
PYTHONPATH=$PYTHONPATH:$DIR

cd serverContext
python ../server/simpleServer.py &

cd ../modules
for i in fnc_*.py
do
   python $i &	
done

cd /mnt/data/data/CALTECH256-2/
while true
do 
    echo ALL OK ---- TESTING
    time ls -1| grep 'jpg$' | gawk '{print "--form file=@" $1 " pchradis:8888/tagging"}' | parallel --jobs 1 'time curl `echo {}; sleep 5`' 
done
