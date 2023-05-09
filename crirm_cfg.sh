#sk user for profilename 
read -p "Enter profile name: " PROFILENAME


# start minikube with specified resources and container runtime
# minikube start -p $PROFILENAME --cpus 10 --memory 20g --disk-size=10g --container-runtime=crio
# minikube start -p $PROFILENAME --container-runtime=crio

 

# create a temporary script file with the commands to run inside minikube
cat > tmp_script.sh << 'EOF'
sudo apt-get update
sudo apt-get install -y git curl make gcc
curl -LO https://golang.org/dl/go1.20.3.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.20.3.linux-amd64.tar.gz
rm go1.20.3.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' | sudo tee -a /etc/profile
source /etc/profile
git clone https://github.com/intel/cri-resource-manager
sed -i '3i export GOMAXPROCS=2' cri-resource-manager/Makefile
cd cri-resource-manager; ulimit -n 65536 && make build && ulimit -n 65536 && sudo make install
sudo cp /etc/cri-resmgr/fallback.cfg.sample /etc/cri-resmgr/fallback.cfg
sudo systemctl enable cri-resource-manager && sudo systemctl start cri-resource-manager
systemctl status cri-resource-manager
EOF

 

# get the IP address and SSH key of the minikube environment
MINIKUBE_IP=$(minikube ip -p $PROFILENAME)
MINIKUBE_SSH_KEY=$(minikube ssh-key -p $PROFILENAME)

 

# copy the temporary script file to the minikube environment using scp
scp -i $MINIKUBE_SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null tmp_script.sh docker@$MINIKUBE_IP:/tmp/tmp_script.sh

 

# SSH into minikube, make the temporary script file executable, and execute it
minikube ssh -p=$PROFILENAME "chmod +x /tmp/tmp_script.sh && /tmp/tmp_script.sh"

 

# remove the temporary script file
rm tmp_script.sh

## set up kublet to use criresmrg as a proxy
sudo vi /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
[Unit]
Wants=crio.service

[Service]
ExecStart=
ExecStart=/var/lib/minikube/binaries/v1.26.3/kubelet --bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --config=/var/lib/kubelet/config.yaml --container-runtime=remote --container-runtime-endpoint=unix:///var/run/cri-resmgr/cri-resmgr.sock --hostname-override=p3 --kubeconfig=/etc/kubernetes/kubelet.conf --node-ip=192.168.49.2

[Install]

# sudo systemctl daemon-reload
# sudo systemctl restart kubelet


sudo cri-resmgr --force-config ~/cri-resource-manager/sample-configs/balloons-policy.cfg --runtime-socket /run/crio/crio.sock 

## messages about failed to connect to socket can be ignored we are using a local configuration file with the --force-config and the agent socket is not is not used in this 


 