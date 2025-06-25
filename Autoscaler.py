# ai_autoscaler.py
from kubernetes import client, config
import requests
import time

SUGGESTION_SERVER_URL = "http://suggestion-server.default.svc.cluster.local:5000/scale"
NAMESPACE = "default"

def get_scaling_suggestion():
    try:
        response = requests.get(SUGGESTION_SERVER_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("deployment_name"), data.get("replicas")
    except Exception as e:
        print(f"[Error] Failed to get suggestion: {e}")
        return None, None

def scale_deployment(deployment_name, replicas):
    try:
        config.load_incluster_config()  # use load_kube_config() for local testing
        apps = client.AppsV1Api()
        deployment = apps.read_namespaced_deployment(deployment_name, NAMESPACE)
        deployment.spec.replicas = replicas
        apps.patch_namespaced_deployment(deployment_name, NAMESPACE, deployment)
        print(f"[Scale] Scaled '{deployment_name}' to {replicas} replicas")
    except Exception as e:
        print(f"[Error] Failed to scale '{deployment_name}': {e}")

if __name__ == "__main__":
    while True:
        deployment_name, replicas = get_scaling_suggestion()
        if deployment_name and replicas is not None:
            scale_deployment(deployment_name, replicas)
        else:
            print("[Info] No action needed this cycle")
        time.sleep(60)
