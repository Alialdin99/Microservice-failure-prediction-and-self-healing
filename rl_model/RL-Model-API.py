from flask import Flask, request, jsonify
import joblib

app = Flask(__name__)

# Load RL model during startup
model = None
try:
    model = joblib.load('final_model.zip')
    print("Model loaded successfully")
except Exception as e:
    print(f"Model loading failed: {str(e)}")
    model = None

def predict_action(metrics):
    """Predict scaling action using RL model"""
    if not model:
        return 1
    
    try:
        features = [
            metrics['cpu_usage'],
            metrics['memory_usage'],
            metrics['network_io']
        ]
        
        prediction = model.predict([features])[0]
        return prediction
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return 1

@app.route('/predict', methods=['POST'])
def predict():
    """Prediction endpoint"""
    try:
        data = request.json
        required_keys = ['cpu_usage', 'memory_usage', 'network_io']
        
        # Validate input
        if not all(key in data for key in required_keys):
            return jsonify({
                "error": "Invalid input format",
                "required_keys": required_keys
            }), 400
        
        # Get prediction
        action = predict_action(data)
        return jsonify({
            "action": action,
            "model_status": "loaded" if model else "not_loaded"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Processing error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False) 