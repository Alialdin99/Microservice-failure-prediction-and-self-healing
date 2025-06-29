# PowerShell script for Windows native execution

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

Write-Host "Installing monitoring framework..."
# Make sure the monitoring script is executable (if using Git Bash or WSL)
if (Test-Path "Monitoring/monitoring-install.ps1") {
    & "Monitoring/monitoring-install.ps1"
} else {
    Write-Host "Warning: monitoring-install.ps1 not found, trying shell script..."
    bash Monitoring/monitoring-install.sh
}

Write-Host "Deploying nginx.yaml..."
kubectl apply -f ./deployments/nginx.yaml

Write-Host "Deploying traffic-generator.yaml..."
kubectl apply -f ./benchmarks/traffic-generator.yaml

Write-Host "Environment setup complete."

Write-Host "Starting Prometheus service in Minikube..."

# Wait for Prometheus pod to be running
Write-Host "Waiting for Prometheus pod to be running..."
do {
    Start-Sleep -Seconds 2
    try {
        $promPod = kubectl get pods -n monitoring -l app=prometheus -o jsonpath="{.items[0].metadata.name}" 2>$null
        if ($promPod) {
            $status = kubectl get pod $promPod -n monitoring -o jsonpath="{.status.phase}" 2>$null
            if ($status -eq "Running") {
                break
            }
        }
    } catch {
        # Continue waiting
    }
} while ($true)

Write-Host "Prometheus pod is running."
# Get the actual Prometheus service name
$promService = kubectl get svc -n monitoring -l app=prometheus -o jsonpath="{.items[0].metadata.name}"
$promUrl = minikube service -n monitoring $promService --url
Write-Host "Prometheus URL: $promUrl"
"PROMETHEUS_URL=$promUrl" | Out-File -FilePath ".env" -Encoding UTF8 