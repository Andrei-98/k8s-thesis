import subprocess
#import os

#subprocess.run(["command", "time", "--verbose", "t-dummy.py"])

#with open("output.txt", "w") as out:
    #for i in range(20):
        #os.system("command time --verbose python3 t-dummy.py > output.txt")
        #subprocess.run(["time", "--verbose", "python3", "t-dummy.py"], stdout=out)

for i in range(20):
    os.system("command time --verbose --output=output2.txt -a python3 t-dummy.py")
    #subprocess.run(["command", "time", "--verbose", "python3", "t-dummy.py", ">>", "output.txt"], shell=True)

print("ran program 20 times!")

# time -f "\t%E real,\t%U user,\t%S sys" ls -Fs


