z = 0
#for i in range(10000000): # 10m, approx 0.8s with 100% CPU
for i in range(1000000):  # 1m
#for i in range(100000): # 100k, approx 0.03s with 97% CPU (threads take ~7-8ms)
        z += 1