# M.A.E.S.T.R.O. - Microservices Autonomous Event Surveillance, Troubleshooting & Recovery Operations

**A proactive, intelligent autoscaling system for Kubernetes that uses Reinforcement Learning to predict and prevent microservice failures before they happen.**

This repository contains the source code for the M.A.E.S.T.R.O. graduation project from Cairo University, Faculty of Computers and Artificial Intelligence.

---

## Table of Contents

- [About The Project](#about-the-project)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Verification and Usage](#verification-and-usage)
- [Training the RL Model](#training-the-rl-model)
- [Project Poster](#project-poster)
- [Team](#team)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## About The Project

Traditional microservice management relies on reactive tools like the Kubernetes Horizontal Pod Autoscaler (HPA). These tools act only *after* a performance threshold (like high CPU usage) has been breached, leading to a delay where application performance suffers. In critical systems like online trading, healthcare, or streaming services, this delay is unacceptable.

**M.A.E.S.T.R.O.** transforms this paradigm from reactive to **proactive**.

Instead of waiting for failures, M.A.E.S.T.R.O. employs a Reinforcement Learning (RL) agent trained to understand the complex dynamics of a microservice environment. By observing a rich set of metrics—including CPU, memory, latency, and request throughput—our system learns the subtle patterns that precede performance degradation and autonomously takes scaling actions to prevent issues before they impact users.

The core of our system is a **Proximal Policy Optimization (PPO)** agent that learns the optimal policy to balance high performance (low latency) with operational cost (minimal pods).

## Key Features

-   🧠 **Intelligent RL-based Autoscaling**: Moves beyond simple metric thresholds to a learned, predictive scaling policy.
-   🚀 **Proactive Failure Prevention**: Aims to scale out *before* latency spikes, ensuring a stable user experience.
-   🛡️ **Resilience-Focused Training**: The RL agent can be trained in an environment with simulated failures (using [Chaos Mesh](https://chaos-mesh.org/)) to build a robust, production-ready policy.
-   🧩 **Decoupled & Modular Architecture**: Built as a set of independent microservices, making the system scalable, maintainable, and easy to upgrade.
-   📊 **Holistic State Representation**: Makes decisions based on a multi-dimensional state vector (`cpu`, `memory`, `replicas`, `latency`, `rps`), providing a complete view of application health.

## System Architecture

M.A.E.S.T.R.O. is composed of four key, decoupled components that work in concert within a Kubernetes cluster.

1.  **Custom Autoscaler**: A Kubernetes controller (the "actuator") that runs in the cluster. It periodically polls the `Suggestion Server` for a scaling action and applies it directly to the target deployment via the Kubernetes API.
2.  **Suggestion Server**: An intermediary API service. It receives requests from the Autoscaler, gathers all necessary real-time metrics from Prometheus, constructs the state vector, and queries the `RL-Model API` for a decision.
3.  **RL-Model API**: A lightweight Flask server that hosts the trained PPO model. Its sole purpose is to receive a state vector and return the optimal action (`Scale Up`, `Scale Down`, or `No-Op`). This decouples the model from the rest of the logic, allowing it to be updated independently.
4.  **Prometheus**: The monitoring backbone. It scrapes and stores all the time-series metrics required by the system.

<!-- You can add an architecture diagram image here -->
<!-- ![Architecture Diagram](./docs/architecture.png) -->


## Tech Stack

| Technology | Role |
| :--- | :--- |
| **Kubernetes** | Core container orchestration platform |
| **Docker** | Containerization |
| **Minikube** | Local Kubernetes development environment |
| **Python 3.8+** | Primary language for RL and API components |
| **Stable Baselines3**| PPO algorithm implementation |
| **Gymnasium (OpenAI Gym)**| Framework for the custom RL environment |
| **PyTorch** | Deep learning framework for the RL policy network |
| **Flask** | Web framework for the `Suggestion Server` and `RL-Model API` |
| **Prometheus** | Monitoring and time-series database |
| **k6** | Load testing and traffic generation |
| **Chaos Mesh** | Chaos engineering for resilience testing |
| **Helm** | Package management for Kubernetes |

## Getting Started

Follow these instructions to deploy and run M.A.E.S.T.R.O. on a local Kubernetes cluster.

### Prerequisites

Ensure you have the following tools installed and configured on your machine:
-   **Docker**: To run containers. [Install Docker](https://docs.docker.com/get-docker/)
-   **Minikube**: For creating a local Kubernetes cluster. [Install Minikube](https://minikube.sigs.k8s.io/docs/start/)
-   **kubectl**: The Kubernetes command-line tool. [Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
-   **Helm**: The package manager for Kubernetes. [Install Helm](https://helm.sh/docs/intro/install/)

Start your Minikube cluster:
```bash
minikube start --cpus=4 --memory=8192

```

---


## Installation

The installation process is divided into three main stages: deploying the monitoring stack, deploying the target application, and deploying the MAESTRO autoscaling components.

### Step 1: Clone the Project Repository

First, clone the repository containing all the necessary Kubernetes YAML files.

```bash
git clone git@github.com:Alialdin99/Microservice-failure-prediction-and-self-healing.git
cd Microservice-failure-prediction-and-self-healing
```

### Step 2: Deploy the Monitoring Stack (Prometheus)

MAESTRO relies on Prometheus to collect the metrics that form the agent's observation state. We will use the official kube-prometheus-stack Helm chart, which provides a comprehensive monitoring solution.

```bash
# 1. Add the Prometheus community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 2. Install the kube-prometheus-stack
# This chart deploys Prometheus, Grafana, and the necessary metric exporters.
helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace
```

### Step 3: Deploy the Target Application & Services

This step deploys the sample application that MAESTRO will autoscale. This deployment includes the application itself, a sidecar for latency metrics, and a Kubernetes Service to expose it.

```bash
# Apply the manifest file for the target application
kubectl apply -f manifests/target-app/deployment.yaml
```

This will create a Deployment, Service, and any other necessary resources for the application you want to scale.

### Step 4: Deploy the MAESTRO Autoscaling System

Now, deploy the three core components of the MAESTRO system. The manifests are structured to create the Deployments, Services, and necessary ServiceAccounts with RBAC permissions.

```bash
# 1. Deploy the RL Model Server
# This pod hosts the trained PPO model.
kubectl apply -f manifests/maestro/rl-model-server.yaml

# 2. Deploy the Suggestion Server
# This service acts as the intermediary.
kubectl apply -f manifests/maestro/suggestion-server.yaml

# 3. Deploy the Custom Autoscaler Controller
# This is the agent that interacts with the K8s API.
# It includes the necessary Role and RoleBinding for scaling deployments.
kubectl apply -f manifests/maestro/autoscaler-controller.yaml
```

After applying these manifests, all components of the MAESTRO system are deployed.

---

## Verification and Usage

### Verifying the Installation

To ensure that all components are running correctly, you can check the status of the pods in the default (or relevant) namespace.

```bash
kubectl get pods
```

**Expected output:**

```text
NAME                                          READY   STATUS    RESTARTS   AGE
target-app-deployment-xxxxxxxxxx-xxxxx        2/2     Running   0          5m
rl-model-server-deployment-xxxxxxxx-xxxxx     1/1     Running   0          2m
suggestion-server-deployment-xxxxxxx-xxxxx    1/1     Running   0          2m
autoscaler-controller-deployment-xxxxxx-xxxxx 1/1     Running   0          1m
```

You can also view the logs of the autoscaler controller to see it making decisions:

```bash
# First, get the name of the autoscaler pod
POD_NAME=$(kubectl get pods -l app=autoscaler-controller -o jsonpath='{.items[0].metadata.name}')

# Then, view its logs
kubectl logs -f $POD_NAME
```

---

### Generating Traffic (Optional)

To see the autoscaler in action, you need to generate load on the target application. The repository includes a manifest to deploy a k6 traffic generator pod.

```bash
# Apply the k6 traffic generator job
kubectl apply -f manifests/tools/k6-traffic-generator.yaml
```

---

### Training the RL Model

For those interested in experimenting or retraining the model, the training script and custom environment are included. The training process uses the `train.py` script, which instantiates our custom `MicroserviceEnv`.

* **Observation Space**: `[cpu_usage, mem_usage, n_replicas, latency, rps]`
* **Action Space**: `[0: Scale Down, 1: No-Op, 2: Scale Up]`
* **Reward Function**: Rewards the agent for keeping latency low and penalizes it for high latency and high resource cost (number of pods).

To start a new training run:

```bash
# (This is a conceptual command)
python train.py --total-timesteps 20000 --save-path models/ppo_new_model
```

---

## Project Poster

<!-- You can add your project poster image here -->

<!-- ![Project Poster](./docs/poster.png) -->

---

## Team

### Supervised By:

* **Dr. Desoky Abdelqawy**

### Implemented By:

* **[Marwan Ahmed Abdelfattah](https://github.com/marwan-ahmedd)**
* **[Amr Khaled El-Hennawi](https://github.com/AmrElHennawi/)**
* **[Mohamed Waleed Mohamed](https://github.com/Dark2343)**
* **[Ali Aldeen Mohamed Hanafy](https://github.com/Alialdin99)**
* **[Zeyad Mohamed Maher Karsoun](https://github.com/KZiad)**

---

## License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE.txt) file for details.

---

## Acknowledgments

* **Cairo University**, Faculty of Computers and Artificial Intelligence
* The teams behind **Stable Baselines3**, **Kubernetes**, and all the open-source tools that made this project possible.
