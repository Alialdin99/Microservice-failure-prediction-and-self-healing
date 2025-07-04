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
bash ./monitoring/monitoring-install.sh

echo "Deploying nginx.yaml..."
kubectl apply -f ./deployments/nginx.yaml

echo "Deploying traffic-generator.yaml..."
kubectl apply -f ./benchmarks/traffic-generator.yaml

echo "Environment setup complete."

echo "Waiting for Prometheus pod to be running..."
sleep 60

echo "Prometheus pod is running."
echo "run in another terminal and keep it running:"
# This is a limitation in running on docker. you need to put this in another terminal that stays up
# This issue is not in the windows hyperv driver
echo "minikube service -n monitoring prometheus-nodeport --url"
echo "and copy the url into the .env file"
