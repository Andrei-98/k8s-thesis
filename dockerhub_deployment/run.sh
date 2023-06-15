#!/bin/sh

#echo START

# for i in 1 2 3 4 5
# do
#     echo "run $i"
#     #./given_sim -c 1 -t 10 -s 64000 -r 1344000 >> output.txt
#     ./given_sim -c 1 -t 10 -s 64000 -r 1344000 >> output.txt

#     # random sleep time 1-50ms
#     #sleep_time=$((RANDOM % 50 + 1))
#     #echo "sleeping for $sleep_time ms"
    
#     #sleep 0.0$sleep_time

#     echo "done $i"
#     python3 ./random_sleep.py
# done

# echo DONE
# echo "finished with tasks! sleeping for 3 minutes for data collection."
# sleep 3m
# echo "finished sleeping."
# sleep 20

echo "container started, sleeping & ready for 10 minutes!"
sleep 420m

