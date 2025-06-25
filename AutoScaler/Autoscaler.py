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
        return data.get("deployment_name"), data.get("replicas"), data.get("action")
    except Exception as e:
        print(f"[Error] Failed to get suggestion: {e}")
        return None, None, None

def apply_scaling(deployment_name, replicas, action):
    try:
        config.load_incluster_config()  # or use load_kube_config() locally
        apps = client.AppsV1Api()
        deployment = apps.read_namespaced_deployment(deployment_name, NAMESPACE)
        current_replicas = deployment.spec.replicas or 1

        if action == "upscale":
            new_replicas = current_replicas + replicas
        elif action == "downscale":
            new_replicas = max(1, current_replicas - replicas)
        elif action == "nothing":
            print("[Info] Action is 'nothing'; skipping scaling")
            return
        else:
            print(f"[Warning] Unknown action '{action}'")
            return

        if new_replicas != current_replicas:
            deployment.spec.replicas = new_replicas
            apps.patch_namespaced_deployment(deployment_name, NAMESPACE, deployment)
            print(f"[Scale] {action} → '{deployment_name}' from {current_replicas} to {new_replicas} replicas")
        else:
            print(f"[Info] No scaling needed; already at {current_replicas} replicas")

    except Exception as e:
        print(f"[Error] Failed to scale deployment '{deployment_name}': {e}")

if __name__ == "__main__":
    while True:
        deployment_name, replicas, action = get_scaling_suggestion()
        if deployment_name and replicas is not None and action:
            apply_scaling(deployment_name, replicas, action)
        else:
            print("[Info] Invalid or empty suggestion; skipping this cycle")
        time.sleep(60)
