import gymnasium as gym
import numpy as np
import time
from gymnasium import spaces
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from reward import RewardCalculator
from kubernetes.client.rest import ApiException as KubernetesException

class MicroserviceEnv(gym.Env):
    def __init__(self):
        super().__init__()
        
        # Action and observation spaces
        self.action_space = spaces.Discrete(3)  # 0=down, 1=nothing, 2=up
        self.observation_space = spaces.Box(
            low=0, high=2**63, shape=(5,), dtype=np.float32
        )
        
        # Kubernetes setup
        config.load_kube_config()
        self.k8s_api = client.AppsV1Api()
        self.deployment_name = "s0"
        self.namespace = "default"
        
        # Prometheus setup
        self.prom = PrometheusConnect(url="http://127.0.0.1:39005")
        self.metric_window = "30s"  # Metrics averaging window
        
        # Time control
        self.action_interval = 10  # Seconds between actions
        
        # Initial seed
        self.np_random = None
        self.reward_calculator = RewardCalculator()

    def reset(self, seed=None, options=None):
        # Initialize RNG
        super().reset(seed=seed)
        self.np_random = np.random.default_rng(seed)
        
        # Reset deployment to 1 pod
        self._scale_pods(1)
        time.sleep(self.action_interval)  # Wait for stabilization
        
        # Get initial state
        state = self._get_state()
        return state, {}

    def step(self, action):
        try:
            # 1. Take scaling action
            current_pods = self._get_current_pods()
            new_pods = current_pods
            
            if action == 0 and current_pods > 1:
                new_pods = current_pods - 1
            elif action == 2:
                new_pods = current_pods + 1

                
            self._scale_pods(new_pods)
            
            # 2. Wait for action interval
            time.sleep(self.action_interval)
            
            # 3. Get new state
            state = self._get_state()
            
            # 4. Calculate reward
            reward = self._calculate_reward(state, action)
            
            # 5. Check termination
            terminated = bool(state[3] > 0.1)  # Error rate >10%
            truncated = False  # No time limit

            if action == 1:
                print(f"Did absolutly nothing | Reward: {reward}")
            elif action == 0:
                print(f"Scaled down to {new_pods} | Reward: {reward}")
            else:
                print(f"Scaled up to {new_pods} | Reward: {reward}")


            return state, reward, terminated, truncated, {}
        except KubernetesException as e:
            print(f"Cluster Failure")
            self.reset()
            return self.observation_space.sample(), -100, True, False, {}

    def _scale_pods(self, replicas: int):
        """Scale the Kubernetes deployment"""
        deployment = self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, namespace=self.namespace
        )
        deployment.spec.replicas = replicas
        self.k8s_api.patch_namespaced_deployment(
            name=self.deployment_name, namespace=self.namespace, body=deployment
        )

    def _get_current_pods(self) -> int:
        """Get current number of pods"""
        deployment = self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, namespace=self.namespace
        )
        return deployment.spec.replicas

    def _get_state(self):
        try:
            queries = {
                "cpu": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}}[1m]))',
                "memory": f'sum(container_memory_working_set_bytes{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}})',
                "latency": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{self.deployment_name}"}}[1m])) by (le)) * 1000',
                "error_rate": f'sum(rate(http_requests_total{{job="{self.deployment_name}", status_code=~"5.."}}[1m])) / sum(rate(http_requests_total{{job="{self.deployment_name}"}}[1m]))'
            }

            cpu_result = self.prom.custom_query(queries["cpu"])
            cpu = float(cpu_result[0]['value'][1]) if cpu_result else 0.0
            memory_result = self.prom.custom_query(queries["memory"])
            memory = float(memory_result[0]['value'][1]) if memory_result else 0.0
            latency_result = self.prom.custom_query(queries["latency"])
            latency = float(latency_result[0]['value'][1]) if latency_result else 0.0
            error_rate_result = self.prom.custom_query(queries["error_rate"])
            error_rate = float(error_rate_result[0]['value'][1]) if error_rate_result else 0.0
            pod_count = self._get_current_pods()

            
            return np.array([cpu, memory, latency, error_rate, pod_count], dtype=np.float32)
                        
        except Exception as e:
            print(f"Error in metric: {str(e)}")
            return np.zeros(...)

    def _calculate_reward(self, state: np.ndarray, action: int) -> float:
        return -self._get_current_pods()
