# Startup Script for the Training Environment
# Make sure you don't have any other minikube instances running and that you have 8GB of memory and 8 CPUs available


# Stop on any error
$ErrorActionPreference = "Stop"

echo "Starting Minikube..."
minikube start --memory 8000 --cpus 8

# Wait for Minikube to be fully running
echo "Waiting for Minikube to be ready..."
do {
    Start-Sleep -Seconds 2
    $status = minikube status --format='{{.Host}}'
} while ($status -ne "Running")

echo "Installing monitoring framework..."
& "monitoring/monitoring-install.ps1"

echo "Deploying nginx.yaml..."
kubectl apply -f ./deployments/nginx.yaml

echo "Deploying traffic-generator.yaml..."
kubectl apply -f ./benchmarks/traffic-generator.yaml

echo "Environment setup complete."

# Wait for Prometheus pod to be running
echo "Waiting for Prometheus pod to be running..."

Start-Sleep -Seconds 60

$promService = "prometheus-nodeport"
$promUrl = minikube service -n monitoring $promService --url
echo "Prometheus URL: $promUrl"
"PROMETHEUS_URL=$promUrl" | Out-File -FilePath ".env" -Encoding UTF8 