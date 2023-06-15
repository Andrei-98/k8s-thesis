Run kubeadm_setup.sh on a fresh ubuntu Ubuntu 22.04.2 LTS x86_64 system. This script will update the system and install all necessary tools for kubeadm and deploy a single node cluster similar to this guide:
https://blog.radwell.codes/2022/07/single-node-kubernetes-cluster-via-kubeadm-on-ubuntu-22-04/

./kubeadm_setup.sh

cri_rm_setup.sh is a follow up to kubeadm_setup. It will install the cri-rm service and configure kublet to use cri-rm as it's container runtime endpoint. It will load in the balloon_policy_configuration in this folder.
./cri_rm_setup.sh

In order to modify the policy change "/etc/cri-resmgr/fallback.cfg" and run 
```sudo systemctl restart cri-resource-manager```

# Example of depoyment using balloon policy

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app-deployment
  labels:
    app: test-app
spec:
  replicas: 13
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
      annotations:
        balloon.balloons.cri-resource-manager.intel.com: quad
    spec:
      containers:
      - name: c-test-app
        image: wryandrei/c-test-app:params
        imagePullPolicy: Always
        ports:
        - containerPort: 80
        resources: 
          requests:
            memory: "64Mi"
            cpu: "25m"
          limits:
            memory: "1G"
            cpu: "210m" 
```

# Ignore Node agent warning: It refers to the node agent not being aviable but we are loading in the configuration through fallback.cfg
```journalctl -u cri-resource-manager -f | grep -v "transport: Error while dialing dial unix /var/run/cri-resmgr/cri-resmgr-agent.sock"```
