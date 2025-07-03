from flask import Flask, request, jsonify
from stable_baselines3 import PPO
from utils.state_builder import StateBuilder
from pathlib import Path

app = Flask(__name__)

# Load the model once when the application starts.
try:
    script_dir = Path(__file__).parent
    model_path = script_dir / "best_model"
    model = PPO.load(str(model_path))
    print("Model loaded successfully.")
except Exception as e:
    print(f"FATAL: Could not load model. Error: {e}")
    model = None

@app.route('/predict', methods=['POST'])
def predict_action():
    if model is None:
        return jsonify({"error": "Model is not loaded on the server"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        # Construct the observation array from the received JSON
        observation = StateBuilder.build_state(
            cpu_usage_percent=data['cpu_usage'],
            memory_bytes=data['memory_usage'],
            n_replicas=data['replicas'],
            p95_latency_ms=data['latency'],
            rps=data['rps']
        )
    except KeyError as e:
        return jsonify({"error": f"Missing key in request: {e}"}), 400

    # Use the loaded model to predict the action
    action, _ = model.predict(observation, deterministic=True)
    
    return jsonify({"action": int(action)})

if __name__ == '__main__':
    # This block is for local testing. In production, Gunicorn runs the app.
    app.run(host='0.0.0.0', port=8000)