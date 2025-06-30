#!/bin/bash

set -e

echo "Installing Chaos Mesh..."

# Create chaos-mesh namespace
kubectl create namespace chaos-mesh --dry-run=client -o yaml | kubectl apply -f -

# Install Chaos Mesh using Helm
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# Install Chaos Mesh with basic configuration
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace=chaos-mesh \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set controllerManager.enableFilterNamespace=true \
  --set controllerManager.targetNamespace=default \
  --set dashboard.enabled=true \
  --set dashboard.service.type=NodePort \
  --set dashboard.service.nodePort=30002

echo "Waiting for Chaos Mesh to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=chaos-mesh -n chaos-mesh --timeout=300s

echo "Chaos Mesh installation complete!"
echo "Dashboard will be available at: http://$(minikube ip):30002"