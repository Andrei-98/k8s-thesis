from kubernetes import client, config
from kubernetes.stream import stream

import os
from os import path
import yaml
import subprocess

import time

import matplotlib.pyplot as plt 
import numpy as np
import seaborn as sns

import asyncio
import json


def plot_graph(bin_arr, job_arr, latency_arr, filename, conversion=True, points=25, hist=False):
    REG_PLOT = True
    MEASURE_GUARANTEE = 10000 # to gather what jobs finish within <10ms

    gathered_data = []

    # for each run
    if not hist:

        # make 1 graph for each run done
        for run in range(len(bin_arr)):

            if REG_PLOT: 
                plt.xlabel("μs")
                plt.ylabel("# jobs")

                #original resolution:
                plt.plot(bin_arr[run], job_arr[run], label="job completion")
                plt.savefig(f"{filename}-job-{run+1}.png")

                plt.plot(bin_arr[run], latency_arr[run], label="latency")

                plt.legend(loc="upper center")
                plt.savefig(f"{filename}-lat-{run+1}.png")
                
                plt.clf()

            if False: # <- temp remove zoomed version
                plt.xlabel("μs")
                plt.ylabel("# jobs")

                # zoomed in version:
                plt.plot(bin_arr[run][:points], job_arr[run][:points], label="job completion")
                plt.savefig(f"{filename}-job-{run+1}-ZOOM.png")

                plt.plot(bin_arr[run][:points], latency_arr[run][:points], label="latency")

                plt.legend(loc="upper center")
                plt.savefig(f"{filename}-lat-{run+1}-ZOOM.png")
                
                plt.clf()


            # stat gathering:
            stats = {"total": sum(job_arr[run]), "<10": 0}

            # histogram attempt: 
            # create a list with each point instead of amount of occurences
            all_data = []
            for c in range(len(bin_arr[run])):
                all_data += [bin_arr[run][c]] * job_arr[run][c]

                if bin_arr[run][c] < MEASURE_GUARANTEE:
                    stats["<10"] += job_arr[run][c]

            gathered_data.append(stats)

            # histogram un-normalized
            if False: #<--- temp removed
                plt.xlabel("μs")
                plt.ylabel("# jobs")

                plt.hist(all_data, bins=20)
                plt.savefig(f"{filename}-hist-{run+1}.png")

                plt.clf()


            np_all_data = np.array(all_data)

            h_plot = sns.histplot(data=np_all_data, stat="probability", bins=10)
            fig = h_plot.get_figure()
            fig.savefig(f"NORM-{filename}-hist-{run+1}.png")

            plt.clf()

        for run in range(len(gathered_data)):
            print(f"run {run+1}: {gathered_data[run]}")


    else:
        for i in range(len(bin_arr)):
            new_edges = bin_arr[i] + [bin_arr[i][-1] + (bin_arr[i][-1] - bin_arr[i][-2])]

            plt.stairs(job_arr[i], new_edges)
            plt.savefig(f"hist-{filename}-job-{i+1}.png")

            plt.clf()


# run this on the server where minikube deployment is, otherwise it won't work
try:
    config.load_kube_config()
    v1 = client.CoreV1Api()
except:
    print("could not load kube config. is kube profile running?")


pod_names = []
running = True

def find_pods(default_print=True, output=True) -> bool:
    global pod_names
    pod_names = []

    try:
        ret = v1.list_namespaced_pod(watch=False, namespace="default")

        if ret and ret.items:
            if output:
                print("Listing relevant pods with their IPs: (%s pods total)" % len(ret.items))

            for i in ret.items:
                if output:
                    if default_print:
                        status = "ok"

                        # override status if pod is locked in waiting (like back-off restart)
                        if i.status.container_statuses[0].state.waiting:
                            if i.status.container_statuses[0].state.waiting.message:
                                status = i.status.container_statuses[0].state.waiting.message.split()[0]

                        print("%s\t%s\t%s" % (i.metadata.name, i.status.phase, status))

                    else:
                        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
                        print(i.status.container_statuses[0].state)
                        print(i.status.phase)
                        print("------------------------------")

                pod_names.append(i.metadata.name)
        
            return True
    except:
        return False


# processes return of subprocess.check_output(...cat output.txt) into nested arrays for each run
# 3 runs -> [[bin-run1],[bin-run2],[bin-run3]], [[j-r1],[j-r2],[j-r3]], [[s-r1],[s-r1],[s-r3]]
def capt_to_arrays(capt):
    rows = capt.split()

    data_started = False

    # Bin[us] Job_comp_time sched_delay
    ends = [" ", " ", "\n"]
    ends_count = 0

    print_buffer = ""

    # toggle this to false to print everything
    PRINT_ONLY_RELEVANT = True

    result = {"bin": [], "job": [], "sched": []}
    run = {"bin": [], "job": [], "sched": []}
    run_amount = 0

    for row in rows:
        if row.decode()[0] == 'B' or row.decode()[0] == 'J':
            continue

        # s in sched_delay, start of new run
        elif row.decode()[0] == 's':
            if not data_started:
                data_started = True

            # don't enter immediately before first run data gather
            if run["bin"]:
                run_amount += 1
                for name in ["bin", "job", "sched"]:
                    result[name].append(run[name])
            run = {"bin": [], "job": [], "sched": []}


        elif data_started:
            print_buffer += f"{row.decode()}{ends[ends_count]}"

            # we should print this
            if ends[ends_count] == "\n":
                # this takes the last three characters and disregards \n
                if PRINT_ONLY_RELEVANT == False or print_buffer[-5:-1] != " 0 0":
                    print(print_buffer, end="")
                
                print_buffer = ""

            # record data to the arrays
            match ends_count:
                case 0:
                    run["bin"].append(int(row.decode()))

                case 1:
                    run["job"].append(int(row.decode()))

                case 2:
                    run["sched"].append(int(row.decode()))

            ends_count += 1

            # reset back to first if done with row
            if ends_count >= len(ends):
                ends_count = 0

        else:
            print(row.decode(), end=" ")


    # add final run as well
    if run["bin"]:
        run_amount += 1
        for name in ["bin", "job", "sched"]:
            result[name].append(run[name])

    # in case of a single run: (changed my mind, this is probably bad)
    #if run_amount == 1:
    #    return run["bin"], run["job"], run["sched"]

    return result["bin"], result["job"], result["sched"]


def exec_one(target=0, retry=False):

    if len(pod_names) == 0:
        print("no pods currently loaded, please run find!")
        return

    print("(receiving data from %s...)" % pod_names[target])

    succeeded, res = get_output(retry, None, target)

    bin_us    = []
    job_comp  = []
    sched_del = []

    if succeeded: # add the received data :-)

        bin_us    = np.array(res[0])
        job_comp  = np.array(res[1])
        sched_del = np.array(res[2])

        plot_graph(bin_us, job_comp, sched_del, f"exec-{target}-test-plot", False)


# needs to be timed correctly :-)
def exec_all(file_count=0, debug_mode=False):
    if debug_mode:
        global pod_names
        pod_names = ["debug"]

    if len(pod_names) == 0 and not debug_mode:
        print("no pods currently loaded, please run find!")
        return


    bin_us    = []
    job_comp  = []
    sched_del = []

    for target in range(len(pod_names)):
        succeeded, res = get_output(False, None, target, file_count, debug_mode)

        if succeeded:
             # if success, add the received data :-)
            res_job, res_lat = [res[1], res[2]]

            if len(bin_us) < 1:
                res_bin = res[0]

                bin_us    = np.array(res_bin)
                job_comp  = np.array(res_job)
                sched_del = np.array(res_lat)

            else:
                job_comp  = np.add(job_comp, np.array(res_job))
                sched_del = np.add(sched_del, np.array(res_lat))

    if len(bin_us) > 0:
        plot_graph(bin_us, job_comp, sched_del, f"{file_count}-combined-test-plot", False)


def get_output(should_retry=True, retry_amount=None, target=0, file_count=0, debug_mode=False):
    #ret = os.system(f"kubectl exec {pod_names[0]} -- cat /app/output.txt")
    #print(ret)

    MAX_RETRIES = 10

    # tc:
    try:
        if debug_mode:
            capt = subprocess.check_output(f"cat ./test_data/output_{file_count}.txt", shell=True)
        else:
            capt = subprocess.check_output(f"kubectl exec {pod_names[target]} -- cat /app/output_{file_count}.txt", shell=True)
    except subprocess.CalledProcessError:
        print(f"--error: no file 'output_{file_count}' for pod {pod_names[target]}--")
        return False, None
    
    if capt:
        print("----")

        res_bin, res_job, res_delay = capt_to_arrays(capt)

        return True, [res_bin, res_job, res_delay]

    else:
        # no response from exec command, await and try again?
        if should_retry:
            print("\nno response, waiting 10 seconds and retrying...")
            for _ in range(10):
                time.sleep(1)
                print(".", end="", flush=True)

            if not retry_amount or retry_amount < MAX_RETRIES:
                if not retry_amount:
                    exec_pod(True, 1)
                else:
                    exec_pod(True, retry_amount+1)

            else:
                return False, None # exceeded max retries (time out)

        else:
            return False, None # failed and retry disabled


def exec_pod(should_retry=True, retry_amount=None, target=0) -> bool:
    
    succeeded, output = get_output(should_retry, retry_amount, target)

    if succeeded:
        plot_graph(output[0], output[1], output[2], f"{target}-test-plot")



# =========================== TEST CASES & 'PROFILES' ==========================================

# automaticall retrieve pods on startup
if find_pods(True, False):
    print(f"pods loaded. ({len(pod_names)} found)")

# global data (yes I know, not the best idea but maybe fine for this project :-) )
profiles = [] # see tc_profiles.json for more details!

# load profiles from the json specified above.
with open("tc_profiles.json") as f:
    profiles = json.load(f)["profiles"]

print("profiles loaded.")
print(profiles)


# HAVE YOU EVER WANTED TO SKIP INPUTTING A TARGET EVERY SINGLE COMMAND?
# NOW INTRODUCING THE FRESH NEW FEATURE THAT WILL PUT ALL OTHER FEATURES TO SHAME
# THEEEE ... TARGETBOTX2000!!!

targeting_mode = False
current_target = 0

# THESE TWO SIMPLE LINES WILL SAVE YOU A WORLD OF TROUBLE!
# AND ALL FOR THE LOW LOW LOOOW PRICE OF
# ...
# NOTHING!

# AMAZING HOW NATURE DOES THAT, HUH?


# id determines which file the output gets stored into, should get stored into "output_(id).txt"
async def tc(target=0, id=0, params="-c 1 -t 10 -s 64000 -r 1344000"):

    print(f"starting process for {pod_names[target]}")
    proc = subprocess.Popen([f"kubectl exec {pod_names[target]} -- /app/tc.sh {id} {params}"], shell=True)

    return proc


async def tc_block(target=0, id=0, params="-c 1 -t 10 -s 64000 -r 1344000", runs=1, transform=False):

    returncodes = []

    # todo: lower range, runs a bit too many times
    for current_run in range(runs):
        #os.system(f"kubectl exec {pod_names[target]} -- /app/tc.sh {id} {params}")

        if transform and (current_run+1 >= transform["occurs_at"] and current_run+1 < transform["occurs_at"]+transform["duration"]):
            proc = await asyncio.create_subprocess_exec("kubectl", "exec", pod_names[target], "--", "/app/tc.sh", str(id), *transform["params"].split())

        else:
            proc = await asyncio.create_subprocess_exec("kubectl", "exec", pod_names[target], "--", "/app/tc.sh", str(id), *params.split())

        returncodes.append(await proc.wait())

    return returncodes


# input to this is a string containing each type and how many should be that kind
# e.g: "LC 10 NLC 10"
async def start_case(params):

    # clean input into {"name": amount}
    words = params.split()

    # error: not even amount of params
    if len(words) % 2 != 0:
        print("error: not even amount of params")
        return

    order_details = {}

    count = 0
    while count < len(words):
        print(f"{words[count]}, {words[count+1]}")

        # add the ordered "profile" (LC etc.) to the dict
        # profile name | amount ordered
        order_details[words[count]] = int(words[count+1])
        count += 2

    # check that we have the correct amount of pods running...
    pods_needed_total = sum(order_details.values())

    if len(pod_names) < pods_needed_total:
        print("error: not enough pods running to fulfill order")
        return


    tasks = []
    target = 0

    # get information for each profile & 
    # start amount of each profile, running according to their settings
    for pr_count, name in enumerate(order_details):
        if name not in profiles:
            print(f"error: no such profile '{name}'")
            return

        # start amount of profile, according to settings
        for i in range(order_details[name]):

            # multi-instance support
            for count, pr_instance in enumerate(profiles[name]["instances"], start=1):
                print(f"debug: starting {pod_names[target]} as {name} ({count})")
                tasks.append(asyncio.ensure_future(tc_block(target, pr_count, pr_instance["params"], pr_instance["run_amount"], pr_instance["transform"])))

            target += 1 # <- multiple instances should go to same target

        print(f"started {i+1} '{name}' tasks!")
    

    # await the finish of the test case
    await asyncio.gather(*tasks)
    print("done with test case!")

    # ------------------------------------

    # create combined graph for all profiles!
    for pr_count in range(len(order_details)):
        exec_all(pr_count)


def logs(target=0):
    os.system(f"kubectl logs {pod_names[target]}")


def top(target=0):
    print(pod_names[target])
    os.system(f"kubectl top pod {pod_names[target]}")


def ls(target=0):
    print(pod_names[target])
    os.system(f"kubectl exec {pod_names[target]} -- ls -la")


def drop(deployment_name="atest-app-deployment"):
    os.system(f"kubectl delete deployment {deployment_name}")
    os.system(f"kubectl delete deployment ncl-deployment")



def start_deployment():
    with open(path.join(path.dirname(__file__), "test-app-deployment.yaml")) as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="default")
        print("Deployment created. status='%s'" % resp.metadata.name)

    with open(path.join(path.dirname(__file__), "test-app-deployment-2.yaml")) as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="default")
        print("Deployment created. status='%s'" % resp.metadata.name)


def let_me_out():
    global running
    running = False


def display_help():
    print("relevant commands:")
    print(" * start: start deployment")
    print(" * drop: drop deployment")
    print(" * find: find all pods")



def cmd(target, command):
    os.system(f"kubectl exec {pod_names[target]} -- {command}")



async def main():
    old_main = True

    while running:

        if old_main:
            actions = {"help": display_help, "start": start_deployment, "drop": drop, 
            "find": find_pods, "exec": exec_one, "logs": logs, "exec-all": exec_all, "top": top,
            "tc": tc, "ls": ls}

            # commands where there is an int arg followed by the rest of input (str) as arg2
            target_param_actions = {"cmd": cmd}

            print("please enter a command:")
            inp = input()

            args = inp.split()

            # has args
            if len(args) > 1:
                if args[0] in actions:

                    if targeting_mode:
                        target =  current_target
                    else:
                        target = int(args[1])

                    # quick fix async
                    if args[0] == "tc":
                        await actions[args[0]](target)

                    else:
                        # currently works for arg 1 is int
                        actions[args[0]](target)


                elif args[0] in target_param_actions:
                    target_param_actions[args[0]](int(args[1]), " ".join(args[2:]))

            elif inp in actions.keys(): # no args
                # quick fix async
                if args[0] == "tc":
                    await actions[inp]()
                else:
                    actions[inp]()

            elif inp == "debug":
                await start_case("LC 1 NLC 1")

            elif inp == "wa":
                # debug no-kube here
                exec_all(0, True)





        # NEW MAIN VERSION: (WIP)
        else:
            no_target_actions = {"help": display_help, "start": start_deployment, "drop": drop,
            "find": find_pods, "exec-all": exec_all, "debug": start_case}

            target_actions = {"cmd": cmd, "exec": exec_one, "logs": logs, "top": top, "tc": tc, "ls": ls}

            t = "none" if not targeting_mode else current_target
            print(f"please enter a command: (target: {t})")
            inp = input()

            args = inp.split()

            # non-targeting:
            if args[0] in no_target_actions:
                if len(args) > 1:
                    pass



        # # exec 1 quick fix
        # elif inp.split()[0] == "exec":
        #     exec_one(target=int(inp.split()[1]))

        # elif inp.split()[0] == "logs":
        #     logs(target=int(inp.split()[1]))

if __name__ == "__main__":
    asyncio.run(main())
