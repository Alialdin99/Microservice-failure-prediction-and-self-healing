# Stop on any error
$ErrorActionPreference = "Stop"

Write-Host "Starting Minikube..."
minikube start

# Wait for Minikube to be fully running
Write-Host "Waiting for Minikube to be ready..."
do {
    Start-Sleep -Seconds 2
    $status = minikube status --format='{{.Host}}'
} while ($status -ne "Running")



Write-Host "Starting Prometheus..."
minikube service -n monitoring prometheus-nodeport