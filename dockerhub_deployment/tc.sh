#!/bin/sh

# save arg1 as run id
run="$1"
shift 1

# pass arguments to this script to the sim
./given_sim "$@" >> "output_$run.txt"

echo DONE
