import requests
from flask import Flask, request, jsonify
import datetime
import os
from utils.prometheus_client import PrometheusClient
from utils.k8s_client import K8sClient
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Configuration
RL_API_URL = os.getenv('RL_API_URL', 'http://model-service:8000/predict') 

# Deployment and namespace for RPS logging
LOG_DEPLOYMENT = os.getenv('LOG_DEPLOYMENT', 'nginx')
LOG_NAMESPACE = os.getenv('LOG_NAMESPACE', 'default')

def log_rps_background():
    prom_client = PrometheusClient()
    rps_query = f'sum(rate(istio_requests_total{{reporter="destination", destination_workload="{LOG_DEPLOYMENT}"}}[1m]))'
    while True:
        try:
            rps = prom_client.query(rps_query)
            logging.info(f"[RPS-LOG] {LOG_NAMESPACE}/{LOG_DEPLOYMENT} RPS: {rps}")
        except Exception as e:
            logging.error(f"[RPS-LOG] Error fetching RPS: {e}")
        time.sleep(10)

# Start the RPS logging thread
rps_thread = threading.Thread(target=log_rps_background, daemon=True)
rps_thread.start()

def fetch_prometheus_metrics(deployment, namespace):
    """Fetch metrics from Prometheus using PrometheusClient and add current replicas from Kubernetes"""
    # Prometheus queries
    PROM_QUERIES = {
    'cpu_usage': f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod=~"{deployment}-.*"}}[1m]))',
    'memory_usage': f'sum(container_memory_usage_bytes{{namespace="{namespace}", pod=~"{deployment}-.*"}})',
    'latency': f'histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload="{deployment}"}}[5m])) by (le))',
    'rps': f'sum(rate(istio_requests_total{{reporter="destination", destination_workload="{deployment}"}}[1m]))'
    }
    metrics = {}
    prom_client = PrometheusClient()
    for name, query in PROM_QUERIES.items():
        value = prom_client.query(query)
        metrics[name] = value
    # Add current replicas from Kubernetes
    try:
        k8s_client = K8sClient(deployment_name=deployment, namespace=namespace)
        metrics['replicas'] = k8s_client.get_current_replicas()
    except Exception as e:
        logging.info(f"Error fetching replicas from Kubernetes: {str(e)}")
        metrics['replicas'] = None
    return metrics

def get_rl_prediction(metrics):
    """Get prediction from RL model API"""
    try:
        response = requests.post(RL_API_URL, json=metrics)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"RL API error : {str(e)}")
    return 1

# Main endpoint for scaling recommendation
@app.route('/suggestion', methods=['GET'])
async def get_suggestion():
    """Endpoint for Kubernetes to get scaling recommendations"""
    try:
        deployment = request.args['deployment']
        namespace = request.args.get('namespace', 'default')
    except KeyError as e:
        return jsonify({"error": f"Missing required query parameter: {e}"}), 400

    # 1. Fetch metrics from Prometheus
    metrics = fetch_prometheus_metrics(deployment=deployment, namespace=namespace)
    if not metrics:
        return jsonify({
            "status": "error",
            "message": "Failed to fetch metrics from Prometheus"
        }), 500
    # 2. Get prediction from RL model
    action = get_rl_prediction(metrics)
    logging.info(f'Action: {action}')
    
    # 3. return suggested action
    return action

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    

if __name__ == '__main__':
    # This block is for local testing. In production, Gunicorn runs the app.
    app.run(host='0.0.0.0', port=5000)