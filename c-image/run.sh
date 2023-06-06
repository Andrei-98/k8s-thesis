#!/bin/bash

# Get the current hour
current_hour=$(date +%H)

if ((current_hour < 1)); then
    ./given_sim -c 4 -t 3600 -s 1100 -r 420000 >> output.txt
    ./given_sim -c 1 -t 5400 -s 1100 -r 420000 >> output.txt
else
    ./given_sim -c 1 -t 5400 -s 1100 -r 420000 >> output.txt
    # Sleep for 420 minutes
fi

echo DONE
sleep 420m