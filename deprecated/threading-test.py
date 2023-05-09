import threading
import time

start_time = []
end_time = []

current_start = 0
current_end = 0
order = ["first", "second", "third"] 



def run_this():
    start_t = time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID)
    global current_start
    global current_end
    print(f"{order[current_start]} thread to execute: {start_t} ns (thread cputime)")
    current_start += 1

    z = 0
    for i in range(10000000): # 10m, approx 4s with 100% CPU
    #for i in range(100000): # 100k, approx 0.03s with 97% CPU (threads take ~7-8ms)
        z += 1

        #y = 0
        #for i in range(5):
        #    y += 1

    print("done!")
    end_time.append(time.clock_gettime_ns(time.CLOCK_REALTIME))

    t = time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID)
    print(f"{order[current_end]} thread to finish: {t} ({t/1000000} ms | {t/1000000000} s) (thread cputime)")
    current_end += 1


threads = []

# start 3 threads
for i in range(3):
    print(f"start thread {i}")
    start_time.append(time.clock_gettime_ns(time.CLOCK_REALTIME))
    t = threading.Thread(target=run_this)
    threads.append(t)
    t.start()

for (i,t) in enumerate(threads):
    print(f"join thread {i}")
    t.join()
    t = end_time[i]-start_time[i]
    print(f"time since start: {t} ({t/1000000} ms | {t/1000000000} s)")