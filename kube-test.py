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

def result_arr_to_int(bin_arr, job_arr, latency_arr):
    new_bin_arr = []
    for b in bin_arr:
        new_bin_arr.append([int(x) for x in b])
    #bin_arr = new_bin_arr

    new_job_arr = []
    for j in job_arr:
        new_job_arr.append([int(x) for x in j])
    #job_arr = new_job_arr

    new_latency_arr = []
    for l in latency_arr:
        new_latency_arr.append([int(x) for x in l])
    #latency_arr = new_latency_arr

    return new_bin_arr, new_job_arr, new_latency_arr


# assumes inp_array is array containing the bin arr, job arr and latency arr
# where each of those contains arrays for each run
def array_contents_to_int(inp_array):
    results = []

    for category in inp_array:
        new_cat_arr = []
        for content in category:
            new_cat_arr.append([int(x) for x in content])
        results.append(new_cat_arr)

    return results[0] if len(results) == 1 else results


def plot_graph(bin_arr, job_arr, latency_arr, filename, conversion=True, points=25, hist=False):
    REG_PLOT = True

    if conversion:
        bin_arr, job_arr, latency_arr = result_arr_to_int(bin_arr, job_arr, latency_arr)


    # for each run
    if not hist:

        # make 1 graph for each run done
        for i in range(len(bin_arr)):

            if REG_PLOT: 
                plt.xlabel("μs")
                plt.ylabel("# jobs")

                #original resolution:
                plt.plot(bin_arr[i], job_arr[i], label="job completion")
                plt.savefig(f"{filename}-job-{i+1}.png")

                plt.plot(bin_arr[i], latency_arr[i], label="latency")

                plt.legend(loc="upper center")
                plt.savefig(f"{filename}-lat-{i+1}.png")
                
                plt.clf()

            if False: # <- temp remove zoomed version
                plt.xlabel("μs")
                plt.ylabel("# jobs")

                # zoomed in version:
                plt.plot(bin_arr[i][:points], job_arr[i][:points], label="job completion")
                plt.savefig(f"{filename}-job-{i+1}-ZOOM.png")

                plt.plot(bin_arr[i][:points], latency_arr[i][:points], label="latency")

                plt.legend(loc="upper center")
                plt.savefig(f"{filename}-lat-{i+1}-ZOOM.png")
                
                plt.clf()


            # histogram attempt: 

            # create a list with each point instead of amount of occurences
            all_data = []
            for c in range(len(bin_arr[i])):
                all_data += [bin_arr[i][c]] * job_arr[i][c]



            # histogram un-normalized
            if False: #<--- temp removed
                plt.xlabel("μs")
                plt.ylabel("# jobs")

                plt.hist(all_data, bins=20)
                plt.savefig(f"{filename}-hist-{i+1}.png")

                plt.clf()

            # normalized:
            #plt.xlabel("μs")
            #plt.ylabel("# jobs")

            #weights = np.ones_like(all_data) / float(len(all_data))

            #plt.hist(all_data, bins=range(1, max(all_data)+2), align="left", weights=weights)
            #plt.xticks(range(1, max(all_data)+1))
            #plt.savefig(f"NORM-{filename}-hist-{i+1}.png")

            np_all_data = np.array(all_data)

            h_plot = sns.histplot(data=np_all_data, stat="probability", bins=10)
            fig = h_plot.get_figure()
            fig.savefig(f"NORM-{filename}-hist-{i+1}.png")

            plt.clf()


    else:
        for i in range(len(bin_arr)):
            new_edges = bin_arr[i] + [bin_arr[i][-1] + (bin_arr[i][-1] - bin_arr[i][-2])]

            plt.stairs(job_arr[i], new_edges)
            plt.savefig(f"hist-{filename}-job-{i+1}.png")

            plt.clf()


# run this on the server where minikube deployment is, otherwise it won't work

config.load_kube_config()

v1 = client.CoreV1Api()


pod_names = []
running = True

def find_pods(default_print=True, output=True):
    global pod_names
    pod_names = []

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


#resp = v1.connect_get_namespaced_pod_exec(pod_names[0], "default", command=exec_command)
#resp = v1.connect_post_namespaced_pod_exec(pod_names[0], "default", command=exec_command)

# processes return of subprocess.check_output(...cat output.txt) into arrays
def capt_to_arrays(capt):
    rows = capt.split()

    data_started = False

    # Bin[us] Job_comp_time sched_delay
    ends = [" ", " ", "\n"]
    ends_count = 0

    print_buffer = ""

    bin_us    = []
    job_comp  = []
    sched_del = []

    #temp_data = []

    # toggle this to false to print everything
    PRINT_ONLY_RELEVANT = True

    for row in rows:
        if not data_started and row.decode() == "0":
            print()

            data_started = True

            print_buffer += f"{row.decode()} "

            bin_us.append(row.decode())

            ends_count += 1



        elif data_started:
            #print(row.decode(), end=ends[ends_count])
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
                    bin_us.append(row.decode())

                case 1:
                    job_comp.append(row.decode())

                case 2:
                    sched_del.append(row.decode())

            ends_count += 1

            # reset back to first if done with row
            if ends_count >= len(ends):
                ends_count = 0

        else:
            print(row.decode(), end=" ")

    return bin_us, job_comp, sched_del


# split the arrays: (on headers)
def split_multiple_outputs(bin_us, job_comp, sched_del):
    res_bin   = []
    while 'Bin[us]' in bin_us:

        # res_bin += [{**this part**},(first_find), ...]
        res_bin.append(bin_us[:bin_us.index('Bin[us]')])

        # bin_us = [...(first_find),{**this part**}]
        bin_us = bin_us[bin_us.index('Bin[us]')+1:]

    res_bin.append(bin_us)


    res_job   = []
    while 'Job_comp_time' in job_comp:
        #job_comp = job_comp.split('Job_comp_time')

        # res_job += [{**this part**},(first_find), ...]
        res_job.append(job_comp[:job_comp.index('Job_comp_time')])

        # job_comp = [...(first_find),{**this part**}]
        job_comp = job_comp[job_comp.index('Job_comp_time')+1:]

    res_job.append(job_comp)


    res_delay = []
    while 'sched_delay' in sched_del:
        #sched_del = sched_del.split('sched_delay')

        # res_delay += [{**this part**},(first_find), ...]
        res_delay.append(sched_del[:sched_del.index('sched_delay')])

        # sched_del = [...(first_find),{**this part**}]
        sched_del = sched_del[sched_del.index('sched_delay')+1:]

    res_delay.append(sched_del)

    return res_bin, res_job, res_delay


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

        # convert the data to int:
        res_bin, res_job, res_lat = array_contents_to_int([res[0], res[1], res[2]])

        bin_us    = np.array(res_bin)
        job_comp  = np.array(res_job)
        sched_del = np.array(res_lat)

        plot_graph(bin_us, job_comp, sched_del, f"exec-{target}-test-plot", False)


# needs to be timed correctly :-)
def exec_all(file_count=0):

    if len(pod_names) == 0:
        print("no pods currently loaded, please run find!")
        return

    #retry_these = []

    bin_us    = []
    job_comp  = []
    sched_del = []

    for target in range(len(pod_names)):
        succeeded, res = get_output(False, None, target)

        if succeeded:
             # if success, add the received data :-)

            # convert the data to int:
            res_job, res_lat = array_contents_to_int([res[1], res[2]])

            if len(bin_us) < 1:
                res_bin = array_contents_to_int([res[0]])

                bin_us    = np.array(res_bin)
                job_comp  = np.array(res_job)
                sched_del = np.array(res_lat)

            else:
                job_comp  = np.add(job_comp, np.array(res_job))
                sched_del = np.add(sched_del, np.array(res_lat))

    if len(bin_us) > 0:
        plot_graph(bin_us, job_comp, sched_del, f"{file_count}-combined-test-plot", False)


def get_output(should_retry=True, retry_amount=None, target=0, file_count=0):
    #ret = os.system(f"kubectl exec {pod_names[0]} -- cat /app/output.txt")
    #print(ret)

    MAX_RETRIES = 10

    # tc:
    try:
        capt = subprocess.check_output(f"kubectl exec {pod_names[target]} -- cat /app/output_{file_count}.txt", shell=True)
    except subprocess.CalledProcessError:
        return False, None
    
    #non-tc:
    #capt = subprocess.check_output(f"kubectl exec {pod_names[target]} -- cat /app/output.txt", shell=True)
    
    if capt:
        print("----")

        bin_us, job_comp, sched_del = capt_to_arrays(capt)
        res_bin, res_job, res_delay = split_multiple_outputs(bin_us, job_comp, sched_del)

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


# supports less than 420 jobs
def status_pod(target=None):

    if len(pod_names) == 0:
        print("no pods currently loaded, please run find!")
        return

    if target:
        capt = subprocess.check_output(f"kubectl logs {pod_names[target]}", shell=True)
        print("todo: fix single-target call")

    else:
        statuses = []
        count = {}
        count.setdefault(-1, 0)
        count.setdefault('*', 0)

        for target in pod_names:
            stdout = subprocess.run(['kubectl', 'logs', target], check=True, capture_output=True, text=True).stdout
            lines = stdout.split('\n')

            found = False
            for line in reversed(lines):
                if line == "DONE":
                    found = True
                    statuses.append(420)
                    count['*'] += 1
                    break 
                elif line[:4] == "done":
                    found = True
                    curr_job = int(line.split()[1]) # "done {2}" <- target digit

                    statuses.append(curr_job)

                    if curr_job not in count:
                        count[curr_job] = 0
                    count[curr_job] += 1
                    break

            if not found:    
                count[-1] += 1
                statuses.append(-1)

        for key in count:
            print(f"{key} | {count[key]}")

    return count

# =========================== TEST CASES & 'PROFILES' ==========================================

# automaticall retrieve pods on startup
find_pods(True, False)
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
    # todo: gather results from each pod

    # create combined graph for all profiles!
    for pr_count in range(len(order_details)):
        exec_all(pr_count)


    # todo: handle the results

    # todo: plot results to graphs
    pass


def logs(target=0):
    os.system(f"kubectl logs {pod_names[target]}")


def top(target=0):
    print(pod_names[target])
    #name = pod_names[target].split('/')[1]
    #os.system(f"kubectl top pod {pod_names[target].split('/')[1]}")
    os.system(f"kubectl top pod {pod_names[target]}")


def ls(target=0):
    print(pod_names[target])
    #name = pod_names[target].split('/')[1]
    #os.system(f"kubectl top pod {pod_names[target].split('/')[1]}")
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

    print("deprecated commands:")
    print(" * status: used print messages to determine status, not working")



def cmd(target, command):
    os.system(f"kubectl exec {pod_names[target]} -- {command}")



async def main():
    old_main = True

    while running:

        if old_main:
            actions = {"help": display_help, "start": start_deployment, "drop": drop, 
            "find": find_pods, "exec": exec_one, "logs": logs, "exec-all": exec_all, "top": top,
            "status": status_pod, "tc": tc, "ls": ls}

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
                await start_case("LC 2 NLC 1")




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
