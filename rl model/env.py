import yaml
import time
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from kubernetes.client.rest import ApiException as KubernetesException
import os
from dotenv import load_dotenv

class MicroserviceEnv(gym.Env):
    def __init__(self, deployment_name='s0', namespace='default'):
        super().__init__()
        load_dotenv()
        self.max_replicas = 15
        
        # Action and observation spaces
        self.action_space = spaces.Discrete(3)  # 0=down, 1=nothing, 2=up
        # [cpu, mem, replicas, latency, rps]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 1, 0, -100], dtype=np.float32),
            high=np.array([500, 1, self.max_replicas, 5000, 100], dtype=np.float32),
            shape=(5,),
            dtype=np.float32
        )
        self.previous_state = np.zeros(self.observation_space.shape, dtype=np.float32)

        # Kubernetes setup
        config.load_kube_config()
        self.k8s_api = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()

        self.deployment_name = deployment_name
        self.namespace = namespace
        
        # Prometheus setup
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        self.prom = PrometheusConnect(url=prometheus_url)
        self.metric_window = "30s"  # Metrics averaging window
        
        # Time control
        self.action_interval = 30  # Seconds between actions
        # Initial seed
        self.np_random = None
        
        # Tracking pod counts
        self.pod_counts = []
        self.steps = []
        self.current_step = 0
        self.max_steps=200
        # Chaos Mesh setup
        self.active_chaos_instances = set()
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
        if self.active_chaos_instances:
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
                self.active_chaos_instances.add(experiment['metadata']['name'])
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
                    self.active_chaos_instances.add(pod_kill_experiment['metadata']['name'])
                    print("Applied pod kill experiment")
                    
            except Exception as e:
                print(f"Failed to inject chaos: {str(e)}")
                return False
        return False

    def _cleanup_chaos(self):
        """Clean up any running chaos experiments"""
        for experiment in self.chaos_experiments.values():
            kind = experiment['kind']
            name = experiment['metadata']['name']
            plural = 'podchaos' if kind == 'PodChaos' else 'stresschaos'
            
            try:
                self.custom_api.delete_namespaced_custom_object(
                    group="chaos-mesh.org",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural=plural,
                    name=name
                )
            except Exception:
                pass  # Ignore if experiment doesn't exist
            
            # Waiting for deletion
            for _ in range(10):
                time.sleep(0.5)
                try:
                    self.custom_api.get_namespaced_custom_object(
                        group="chaos-mesh.org",
                        version="v1alpha1",
                        namespace=self.namespace,
                        plural=plural,
                        name=name
                    )
                except:
                    # deleted successfully
                    break

            if name in self.active_chaos_instances:
                self.active_chaos_instances.discard(name)
                print(f"Deleted {kind} chaos experiment")
    
    def reset(self, seed=None, options=None):
        # Initialize RNG
        super().reset(seed=seed)
        self.np_random = np.random.default_rng(seed)
        
        time.sleep(self.action_interval)  # Wait for stabilization
        self._scale_pods(self._get_current_replicas())
        time.sleep(self.action_interval)  # Wait for stabilization
        
        # Get initial state
        state = self._get_state()
        self.current_step = 0
        return state, {}

    def step(self, action):
        try:
            state = self._get_state()
            print(state, end=' ')
            replicas = int(state[2])
            replica_change = action - 1
            target_replica = replicas + replica_change
            
            if replica_change == 0:
                print(f"No scaling (replicas remain {replicas}),", end=' ')
            elif target_replica < 1 or target_replica > self.max_replicas:
                print(f"Invalid action, Reward: -1")
                return state, -1, True, False, {
                    'current_replicas': replicas,
                    'action': action,
                    'invalid_action': True,
                    'cpu_usage': state[0],
                    'memory_usage': state[1],
                    'response_time': state[2]
                }
            else:
                self._scale_pods(target_replica)
                print(f"Scaled to {target_replica} replicas,", end=' ')
              
            # Clean up any existing chaos experiments
            # self._cleanup_chaos()

            # 2. Inject chaos (randomly)
            # if not self.active_chaos_instances:
            #     self._inject_chaos()
                
            # No need for fixed wait time - pods are already ready from _scale_pods

            # 2. Get new state
            new_state = self._get_state()
            
            # Debug information for latency tracking
            if replica_change != 0:
                latency_change = new_state[3] - state[3]
                print(f"Latency change: {latency_change:.2f}ms (from {state[3]:.2f} to {new_state[3]:.2f})", end=' ')

            # 3. Calculate reward
            reward, done = self._calculate_reward(new_state)
            print(f'Reward: {reward:.4f}')

            # Track pod counts
            self.current_step += 1
            self.steps.append(self.current_step)
            self.pod_counts.append(target_replica)

            # Check for max steps
            if self.current_step >= self.max_steps:
                return new_state, reward, False, True, {
                    'current_replicas': target_replica,
                    'action': target_replica,
                    'cpu_usage': new_state[0],
                    'memory_usage': new_state[1],
                    'response_time': new_state[2],
                    'reward': reward,
                    'truncated': True
                }
            
            return new_state, reward, done, False, {
                'current_replicas': target_replica,
                'action': action,
                'cpu_usage': new_state[0],
                'memory_usage': new_state[1],
                'response_time': new_state[2],
                'reward': reward
            }
        except KubernetesException as e:
            # Specific handling for k8s errors
            print(f"Kubernetes API Error: {e.reason}, Reward: -50")
            state = self._get_state()
            return state, -50, True, False, {'error': e.reason}
        except Exception as e:
            print(f"Unexpected error in step: {str(e)}")
            return state, -10, True, False, {
                'error': str(e),
                'current_replicas': self._get_current_replicas(),
                'unexpected_error': True
            }

    def _wait_for_pods_ready(self, expected_replicas: int, timeout: int = 60):
        """Wait for pods to be ready after scaling"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Get deployment status
                deployment = self.k8s_api.read_namespaced_deployment(
                    name=self.deployment_name, namespace=self.namespace
                )
                
                # Check if desired replicas match expected
                if deployment.spec.replicas != expected_replicas:
                    print(f"Deployment replicas mismatch: expected {expected_replicas}, got {deployment.spec.replicas}")
                    return False
                
                # Check if all pods are ready
                if (deployment.status.ready_replicas == expected_replicas and 
                    deployment.status.available_replicas == expected_replicas):
                    print(f"All {expected_replicas} pods are ready")
                    return True
                
                print(f"Waiting for pods: {deployment.status.ready_replicas}/{expected_replicas} ready")
                time.sleep(2)
                
            except Exception as e:
                print(f"Error checking pod readiness: {str(e)}")
                time.sleep(2)
        
        print(f"Timeout waiting for {expected_replicas} pods to be ready")
        return False

    def _scale_pods(self, replicas: int):
        """Scale the Kubernetes deployment"""
        # Get the latest deployment state
        deployment = self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, 
            namespace=self.namespace
        )
        
        # Update the replicas
        deployment.spec.replicas = int(replicas)
        
        # Apply the update
        self.k8s_api.patch_namespaced_deployment(
            name=self.deployment_name, 
            namespace=self.namespace, 
            body=deployment
        )
        
        # Wait for pods to be ready
        if not self._wait_for_pods_ready(replicas):
            print(f"Warning: Pods may not be fully ready after scaling to {replicas} replicas")
        else:
            # Small stabilization period for load balancer to distribute traffic
            time.sleep(3)

    def _get_current_replicas(self) -> int:
        """Get current number of pods"""
        deployment = self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, namespace=self.namespace
        )
        return deployment.spec.replicas

    def _get_annotations(self):
        deployment = self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, namespace=self.namespace
        )
        return deployment.metadata.annotations or {}

    def _get_state(self):
        try:
            # --- Get Core Metrics ---
            cpu_query = self.prom.custom_query(f'sum(rate(container_cpu_usage_seconds_total{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}}[1m])) * 100')
            cpu_usage_percent = float(cpu_query[0]['value'][1]) if cpu_query else 0.0
            
            memory_query = self.prom.custom_query(f'sum(container_memory_working_set_bytes{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}})')
            memory_bytes = float(memory_query[0]['value'][1]) if memory_query else 0.0
            
            # --- Get Application Performance (Latency & RPS) ---
            # p95 latency (ms) - improved query with better time window
            p95_query = self.prom.custom_query(
                f'histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload="{self.deployment_name}"}}[5m])) by (le))'
            )
            p95_latency_ms = float(p95_query[0]['value'][1]) if p95_query else 0.0

            # RPS (requests per second)
            rps_query = self.prom.custom_query(
                f'sum(rate(istio_requests_total{{reporter="destination", destination_workload="{self.deployment_name}"}}[1m]))'
            )
            rps = float(rps_query[0]['value'][1]) if rps_query else 0.0

            # --- Get Pod Count ---
            n_replicas = self._get_current_replicas()
            
            # --- Normalize Memory ---
            max_memory_per_pod = 512 * 1024 * 1024 # 512MiB
            total_max_memory = max_memory_per_pod * n_replicas
            memory_normalized = memory_bytes / total_max_memory if total_max_memory > 0 else 0.0

            # --- Assemble State ---
            current_state = np.array([
                cpu_usage_percent,
                memory_normalized,
                n_replicas,
                p95_latency_ms,
                rps
            ], dtype=np.float32)
            
            # Update previous state for the next step
            self.previous_state = current_state
            return current_state
        except Exception as e:
            print(f"Error getting state: {str(e)}")
            # Return a zeroed array that matches the space shape
            return np.zeros(self.observation_space.shape, dtype=np.float32)
        
    def _calculate_reward(self, new_state: np.ndarray) -> float:
        annotations = self._get_annotations()
        r1 = (self.max_replicas - new_state[2]) / self.max_replicas
        
        r2 = 0
        terminated = False
        latency = new_state[3]
        latencySoftConstraint = float(annotations.get('latencySoftConstraint', -1))
        latencyHardConstraint = float(annotations.get('latencyHardConstraint', -1))
        if latencySoftConstraint != -1 and latencyHardConstraint != -1:
            if latency > latencyHardConstraint:
                r2 = 0
                terminated = True
            elif latencySoftConstraint < latency <= latencyHardConstraint:
                r2 = 0.5
            elif latency <= latencySoftConstraint:
                r2 = 1

        reward = r1 + r2
        return reward, terminated

    def get_pod_history(self):
        """Return the history of pod counts and steps"""
        return self.steps, self.pod_counts
