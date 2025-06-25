import requests
from flask import Flask, request, jsonify
import datetime
import os
import joblib
import time

app = Flask(__name__)

# Configuration
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090/api/v1/query')
RL_API_URL = os.getenv('RL_API_URL', 'http://localhost:5000/predict') 

# Prometheus queries
PROM_QUERIES = {
    "cpu_usage": '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100',
    "memory_usage": '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))',
    "network_io": 'rate(node_network_receive_bytes_total[1m])'
}

def fetch_prometheus_metrics():
    """Fetch metrics from Prometheus with retries"""
    metrics = {}
    max_retries = 3
    for name, query in PROM_QUERIES.items():
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    PROMETHEUS_URL,
                    params={'query': query},
                    timeout=3
                )
                response.raise_for_status()
                result = response.json().get('data', {}).get('result')
                
                if not result:
                    print(f"No results for query: {query}")
                    continue
                    
                value = result[0].get('value', [None, None])[1]
                if value is None:
                    print(f"Value missing for query: {query}")
                    continue
                    
                metrics[name] = float(value)
                break  
                
            except Exception as e:
                print(f"Metrics fetch error (attempt {attempt+1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1) 
                else:
                    metrics[name] = 0.0  
    return metrics

def get_rl_prediction(metrics):
    """Get prediction from RL model API with retries"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                RL_API_URL,
                json=metrics,
                timeout=3
            )
            response.raise_for_status()
            return response.json().get('action')
        except Exception as e:
            print(f"RL API error (attempt {attempt+1}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(0.5)
    return 1

# Main endpoint for scaling recommendation
@app.route('/scale', methods=['POST'])
def scale_recommendation():
    """Endpoint for Kubernetes to get scaling recommendations"""
    start_time = time.time()
    
    # 1. Fetch metrics from Prometheus
    metrics = fetch_prometheus_metrics()
    if not metrics:
        return jsonify({
            "status": "error",
            "message": "Failed to fetch metrics from Prometheus"
        }), 500
    
    # 2. Get prediction from RL model
    action = get_rl_prediction(metrics)

    # 3. Prepare response
    response = {
        "status": "success",
        "action": action,
        "processing_time": round(time.time() - start_time, 4)
    }
    
    return jsonify(response)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    print("Starting Kubernetes Scaling Recommendation API...")
    print(f"Prometheus URL: {PROMETHEUS_URL}")
    print(f"RL Model API URL: {RL_API_URL}")
    app.run(host='0.0.0.0', port=5000, debug=False)