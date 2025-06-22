import joblib
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)

# store latest prediction
latest_prediction = {
    "action": None,
    "timestamp": None,
    "metrics": None
}

# Load RL model 
try:
    model = joblib.load('final_model.zip')
    print("Model loaded successfully")
except Exception as e:
    print(f"Model loading failed: {str(e)}")
    model = None

# Configuration
PROMETHEUS_URL = "http://prometheus:9090/api/v1/query" #dummy
KUBERNETES_PLUGIN_URL = "http://kubernetes-plugin/api/scale" #dummy
PROM_QUERIES = {
    "cpu_usage": '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100',
    "memory_usage": '100 * (1 - ((node_memory_MemAvailable_bytes) / (node_memory_MemTotal_bytes)))',
    "network_io": 'irate(node_network_receive_bytes_total[5m])'
}

def fetch_prometheus_metrics():
    """Fetch metrics from Prometheus"""
    metrics = {}
    try:
        for name, query in PROM_QUERIES.items():
            response = requests.get(PROMETHEUS_URL, params={'query': query})
            response.raise_for_status()
            result = response.json()['data']['result'][0]['value'][1]
            metrics[name] = float(result)
        print(f"Metrics fetched: {metrics}")
        return metrics
    except Exception as e:
        print(f"Metrics fetch error: {str(e)}")
        return None

def predict_action(metrics):
    """Predict scaling action using RL model"""
    if not model:
        return "no_action"
    
    try:
        features = [
            metrics['cpu_usage'],
            metrics['memory_usage'],
            metrics['network_io']
        ]
        
        prediction = model.predict([features])[0]
        actions = {0: "scale_down", 1: "no_action", 2: "scale_up"}
        return actions.get(prediction, "no_action")
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return "no_action"

def send_to_kubernetes(action):
    """Send scaling action to Kubernetes plugin"""
    try:
        payload = {"action": action}
        response = requests.post(KUBERNETES_PLUGIN_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Sent to Kubernetes: {action}")
        return True
    except Exception as e:
        print(f"Kubernetes comm error: {str(e)}")
        return False

def hourly_task():
    """Scheduled task that runs every hour"""
    global latest_prediction
    
    print("\nRunning hourly task...")
    metrics = fetch_prometheus_metrics()
    if not metrics:
        return
        
    action = predict_action(metrics)
    send_to_kubernetes(action)
    
    # Store prediction for user display
    latest_prediction = {
        "action": action,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "metrics": metrics
    }
    print(f"New prediction stored: {action}")

# User endpoint to show latest prediction
@app.route('/prediction', methods=['GET'])
def get_prediction():
    return jsonify({
        "status": "success" if latest_prediction['action'] else "no_data",
        "prediction": latest_prediction
    })

if __name__ == '__main__':
    # Setup scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(hourly_task, 'interval', hours=1)
    scheduler.start()
    
    # Initial run
    hourly_task()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)