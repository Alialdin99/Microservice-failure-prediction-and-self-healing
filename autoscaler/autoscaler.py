import requests
import time
from utils.k8s_client import K8sClient
import os
import logging

logging.basicConfig(level=logging.INFO)

SUGGESTION_SERVICE_URL = os.getenv("SUGGESTION_SERVICE_URL", "http://suggestion-service:5000/suggestion")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60))
NAMESPACE = "default"
DEPLOYMENT = 'nginx'

client = K8sClient(deployment_name=DEPLOYMENT, namespace=NAMESPACE)

def get_scaling_suggestion():
    try:
        params = {
            'deployment': DEPLOYMENT,
            'namespace': NAMESPACE
        }
        response = requests.get(SUGGESTION_SERVICE_URL, params=params)
        response.raise_for_status()
        action = response.json()['action']
        return action
    except Exception as e:
        logging.error(f"[Error] Failed to get suggestion: {e}")
        return None

def perform_scaling_action(action):
    try:
        
        current_replicas = client.get_current_replicas()
        new_replicas = max(1, current_replicas + action - 1)
        
        if new_replicas != current_replicas:
            client.scale_deployment(new_replicas)
            logging.info(f"[Scale] {action} → '{DEPLOYMENT}' from {current_replicas} to {new_replicas} replicas")
        else:
            logging.info(f"[Info] No scaling needed; already at {current_replicas} replicas")

    except Exception as e:
        logging.error(f"[Error] Failed to scale deployment '{DEPLOYMENT}': {e}")

if __name__ == "__main__":
    logging.info("Starting Custom autoscaler Controller...")
    while True:
        logging.info(f"--- New cycle for {NAMESPACE}/{DEPLOYMENT} ---")
        action = get_scaling_suggestion()
        if action is not None:
            perform_scaling_action(action)
        logging.info(f"--- Cycle complete. Waiting for {POLL_INTERVAL_SECONDS} seconds. ---")
        time.sleep(POLL_INTERVAL_SECONDS)
