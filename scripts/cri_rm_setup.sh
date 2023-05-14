# on ubuntu
sudo apt install jq
CRIRM_VERSION=`curl -s "https://api.github.com/repos/intel/cri-resource-manager/releases/latest" | jq .tag_name | tr -d '"v'`
source /etc/os-release
pkg=cri-resource-manager_${CRIRM_VERSION}_${ID}-${VERSION_ID}_amd64.deb; curl -LO https://github.com/intel/cri-resource-manager/releases/download/v${CRIRM_VERSION}/${pkg}; sudo dpkg -i ${pkg}; rm ${pkg}

# create configuration and start cri-resoruce-manager
sudo cp balloon.cfg /etc/cri-resmgr/fallback.cfg
sudo systemctl enable cri-resource-manager && sudo systemctl start cri-resource-manager


# check if service is active
if systemctl is-active --quiet cri-resource-manager; then
    echo "The cri-resource-manager service is active."
else
    echo "WARNING: The cri-resource-manager service is not active."
fi

sudo touch /etc/default/kubelet
echo 'KUBELET_EXTRA_ARGS=--container-runtime-endpoint=/var/run/cri-resmgr/cri-resmgr.sock' | sudo tee /etc/default/kubelet
sudo systemctl daemon-reload
sudo systemctl restart kubelet