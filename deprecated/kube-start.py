from os import path
import yaml

from kubernetes import client, config

def main():
    config.load_kube_config()

    with open(path.join(path.dirname(__file__), "test-app-deployment.yaml")) as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="default")
        print("Deployment created. status='%s'" % resp.metadata.name)


if __name__=='__main__':
    main()