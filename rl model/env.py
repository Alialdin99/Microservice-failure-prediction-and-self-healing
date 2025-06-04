import yaml
import time
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from kubernetes.client.rest import ApiException as KubernetesException

class MicroserviceEnv(gym.Env):
    def __init__(self):
        super().__init__()
        
        # Action and observation spaces
        self.action_space = spaces.Discrete(3)  # 0=down, 1=nothing, 2=up
        self.observation_space = spaces.Box(
            low=0, high=2**63, shape=(3,), dtype=np.float32
        )
        
        # Kubernetes setup
        config.load_kube_config()
        self.k8s_api = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
        self.deployment_name = "nginx-deployment"
        self.namespace = "default"
        
        # Prometheus setup
        self.prom = PrometheusConnect(url="http://127.0.0.1:34809")
        self.metric_window = "30s"  # Metrics averaging window
        
        # Time control
        self.action_interval = 5  # Seconds between actions
        self.max_pods = 15
        # Initial seed
        self.np_random = None
        
        # Tracking pod counts
        self.pod_counts = []
        self.steps = []
        self.current_step = 0
        
        # Chaos Mesh setup
        self.chaos_active = False
        self.chaos_experiments = {
            'cpu_stress_failure': {
                'apiVersion': 'chaos-mesh.org/v1alpha1',
                'kind': 'StressChaos',
                'metadata': {
                    'name': 'cpu-stress',
                    'namespace': self.namespace
                },
                'spec': {
                    'mode': 'all',
                    'selector': {
                        'labelSelectors': {
                            'app': self.deployment_name
                        }
                    },
                    'stressors': {
                        'cpu': {
                            'workers': 4,
                            'load': 100
                        }
                    },
                    'duration': '270s' # 4.5 mins
                }
            },
            'pod_kill': {
                'apiVersion': 'chaos-mesh.org/v1alpha1',
                'kind': 'PodChaos',
                'metadata': {
                    'name': 'pod-kill',
                    'namespace': self.namespace
                },
                'spec': {
                    'action': 'pod-kill',
                    'mode': 'all',
                    'selector': {
                        'labelSelectors': {
                            'app': self.deployment_name
                        }
                    },
                }
            },
            'cpu_stress': {
                'apiVersion': 'chaos-mesh.org/v1alpha1',
                'kind': 'StressChaos',
                'metadata': {
                    'name': 'cpu-stress',
                    'namespace': self.namespace
                },
                'spec': {
                    'mode': 'all',
                    'selector': {
                        'labelSelectors': {
                            'app': self.deployment_name
                        }
                    },
                    'stressors': {
                        'cpu': {
                            'workers': 4,
                            'load': 50
                        }
                    },
                    'duration': '270s' # 4.5 mins
                }
            }
        }

    def _inject_chaos(self):
        if self.chaos_active:
            return False
        
        """Randomly inject a chaos experiment (cpu_stress or cpu_stress_failure only)"""
        if random.random() < 0.1:  # 10% chance to inject chaos
            experiment = random.choice([
                self.chaos_experiments['cpu_stress'],
                self.chaos_experiments['cpu_stress_failure']
            ])
            try:
                self.custom_api.create_namespaced_custom_object(
                    group="chaos-mesh.org",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural="stresschaos",
                    body=experiment
                )
                print(f"Injected {experiment['kind']} chaos experiment")

                # If the experiment is cpu_stress_failure, apply pod kill
                if experiment == self.chaos_experiments['cpu_stress_failure']:
                    pod_kill_experiment = self.chaos_experiments['pod_kill']
                    self.custom_api.create_namespaced_custom_object(
                        group="chaos-mesh.org",
                        version="v1alpha1",
                        namespace=self.namespace,
                        plural="podchaos",
                        body=pod_kill_experiment
                    )
                    print("Applied pod kill experiment")
                    
                    # Set the chaos_active flag to True
                self.chaos_active = True
            except Exception as e:
                print(f"Failed to inject chaos: {str(e)}")
                return False
        return False

    def _cleanup_chaos(self):
        """Clean up any running chaos experiments"""
        for experiment in self.chaos_experiments.values():
            try:
                self.custom_api.delete_namespaced_custom_object(
                    group="chaos-mesh.org",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural="podchaos" if experiment['kind'] == 'PodChaos' else "stresschaos",
                    name=experiment['metadata']['name']
                )
            except Exception:
                pass  # Ignore if experiment doesn't exist
        self.chaos_active = False

    def reset(self, seed=None, options=None):
        # Initialize RNG
        super().reset(seed=seed)
        self.np_random = np.random.default_rng(seed)
        
        # Reset deployment to 1 pod
        self._scale_pods(self._get_current_pods())
        time.sleep(self.action_interval)  # Wait for stabilization
        
        # Get initial state
        state = self._get_state()
        return state, {}

    def step(self, action):
        try:
            # 1. Take scaling action
            current_pods = self._get_current_pods()
            new_pods = current_pods
            state = self._get_state()

            if action == 0 and current_pods == 1 or action == 2 and current_pods == self.max_pods:
                print(f"Invalid action, Reward: -10")
                return state, -1, True, False, {
                    'current_pods': current_pods,
                    'action': action,
                    'invalid_action': True,
                    'cpu_usage': state[0],
                    'memory_usage': state[1],
                    'response_time': state[2]
                }
            
            if action == 0:
                new_pods = current_pods - 1
            elif action == 2:
                new_pods = current_pods + 1

            if not self._scale_pods(new_pods):
                print("Failed to scale up, keeping current pod count")
                new_pods = current_pods

            # 1. Wait for stablization
            time.sleep(self.action_interval)

            # 2. Get new state
            new_state = self._get_state()

            # 3. Calculate reward
            reward = self._calculate_reward(state, action, new_state)

            # Track pod counts
            self.current_step += 1
            self.steps.append(self.current_step)
            self.pod_counts.append(new_pods)

            if action == 1:
                print(f"Did nothing, Reward: {reward}")
            elif action == 0:
                print(f"Scaled down to {new_pods}, Reward: {reward}")
            else:
                print(f"Scaled up to {new_pods}, Reward: {reward}")

            return new_state, reward, False, False, {
                'current_pods': new_pods,
                'action': action,
                'cpu_usage': new_state[0],
                'memory_usage': new_state[1],
                'response_time': new_state[2],
                'reward': reward
            }
        except Exception as e:
            print(f"Unexpected error in step: {str(e)}")
            return state, -10, True, False, {
                'error': str(e),
                'current_pods': self._get_current_pods(),
                'unexpected_error': True
            }

    def _scale_pods(self, replicas: int):
        """Scale the Kubernetes deployment"""
        # Get the latest deployment state
        deployment = self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, 
            namespace=self.namespace
        )
        
        # Update the replicas
        deployment.spec.replicas = replicas
        
        # Apply the update
        self.k8s_api.patch_namespaced_deployment(
            name=self.deployment_name, 
            namespace=self.namespace, 
            body=deployment
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
                "cpu_usage_percent": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}}[1d])) * 100',
                "memory": f'sum(container_memory_working_set_bytes{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}})',
            }
            # Get CPU usage
            cpu_query = self.prom.custom_query(queries["cpu_usage_percent"])
            cpu_usage_percent = float(cpu_query[0]['value'][1]) if cpu_query else 0.0
            
            # Get memory usage
            memory_query = self.prom.custom_query(queries["memory"])
            memory = float(memory_query[0]['value'][1]) if memory_query else 0.0
            
            # Get current pod count
            pod_count = self._get_current_pods()

            return np.array([cpu_usage_percent, memory, pod_count], dtype=np.float32)
        except Exception as e:
            print(f"Error in metric: {str(e)}")
            return np.zeros(3, dtype=np.float32)
        
    def _calculate_reward(self, state: np.ndarray, action: int, next_state: np.ndarray) -> float:
        return (self.max_pods - self._get_current_pods()) / self.max_pods

    def get_pod_history(self):
        """Return the history of pod counts and steps"""
        return self.steps, self.pod_counts
