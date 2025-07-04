echo "Setting up Kubernetes configuration..."

# Prometheus
echo "Creating monitoring namespace..."
kubectl create namespace monitoring

echo "Adding Prometheus Helm repository..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

echo "Installing Prometheus stack..."
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

# Prometheus (30000) and Grafana (30001) NodePort Services
echo "Applying NodePort services..."
kubectl apply -f ./monitoring/prometheus-nodeport.yaml -n monitoring
kubectl apply -f ./monitoring/grafana-nodeport.yaml -n monitoring

# Istio
echo "Setting up Istio..."
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update
kubectl create namespace istio-system
helm install istio-base istio/base -n istio-system
helm install istiod istio/istiod -n istio-system --set global.proxy.tracer="zipkin" --wait
helm install istio-ingressgateway istio/gateway -n istio-system
kubectl label namespace default istio-injection=enabled

# Istio - Prometheus integration
echo "Applying Istio-Prometheus integration..."
kubectl apply -f ./monitoring/istio-prometheus-operator.yaml

echo "Monitoring installation complete!" 