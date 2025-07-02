from flask import Flask, request, jsonify
from stable_baselines3 import PPO
import numpy as np

app = Flask(__name__)

# Load the model once when the application starts.
try:
    model = PPO.load("/app/your_model.zip")
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
        observation = np.array([
            data['cpu_usage'],
            data['mem_usage'],
            data['n_replicas'],
            data['latency'],
            data['rps']
        ], dtype=np.float32)
    except KeyError as e:
        return jsonify({"error": f"Missing key in request: {e}"}), 400

    # Use the loaded model to predict the action
    action, _ = model.predict(observation, deterministic=True)
    
    return jsonify({"action": int(action)})

if __name__ == '__main__':
    # This block is for local testing. In production, Gunicorn runs the app.
    app.run(host='0.0.0.0', port=8000)