# PowerShell script for Windows native execution

# Secure .kube (Windows equivalent)
# Note: Windows file permissions work differently than Unix
# This is a placeholder for the chmod equivalent
Write-Host "Setting up Kubernetes configuration..."

# Prometheus
Write-Host "Creating monitoring namespace..."
kubectl create namespace monitoring

Write-Host "Adding Prometheus Helm repository..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

Write-Host "Installing Prometheus stack..."
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

# Prometheus (30000) and Grafana (30001) NodePort Services
Write-Host "Applying NodePort services..."
kubectl apply -f ./Monitoring/prometheus-nodeport.yaml -n monitoring
kubectl apply -f ./Monitoring/grafana-nodeport.yaml -n monitoring

# Istio
Write-Host "Setting up Istio..."
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update
kubectl create namespace istio-system
helm install istio-base istio/base -n istio-system
helm install istiod istio/istiod -n istio-system --set global.proxy.tracer="zipkin" --wait
helm install istio-ingressgateway istio/gateway -n istio-system
kubectl label namespace default istio-injection=enabled

# Istio - Prometheus integration
Write-Host "Applying Istio-Prometheus integration..."
kubectl apply -f ./Monitoring/istio-prometheus-operator.yaml

Write-Host "Monitoring installation complete!" 