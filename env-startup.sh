#!/bin/bash

set -e

echo "Starting Minikube..."
minikube start

# Wait for Minikube to be fully running
echo "Waiting for Minikube to be ready..."
while [[ $(minikube status --format='{{.Host}}') != "Running" ]]; do
  sleep 2
done

echo "Installing monitoring framework..."
chmod +x monitoring/monitoring-install.sh
./monitoring/monitoring-install.sh

echo "Deploying nginx.yaml..."
kubectl apply -f ./deployments/nginx.yaml

echo "Deploying traffic-generator.yaml..."
kubectl apply -f ./benchmarks/traffic-generator.yaml

echo "Environment setup complete."

echo "Starting Prometheus service in Minikube..."

# Wait for Prometheus pod to be running
PROM_POD=""
echo "Waiting for Prometheus pod to be running..."
while true; do
  PROM_POD=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || true)
  STATUS=$(kubectl get pod "$PROM_POD" -n monitoring -o jsonpath="{.status.phase}" 2>/dev/null || true)
  if [[ "$STATUS" == "Running" ]]; then
    break
  fi
  sleep 2
done

echo "Prometheus pod is running."
PROM_URL=$(minikube service -n monitoring prometheus-nodeport --url)
echo "Prometheus URL: $PROM_URL"
echo "PROMETHEUS_URL=$PROM_URL" > .env
