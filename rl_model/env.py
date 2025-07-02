import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from kubernetes.client.rest import ApiException as KubernetesException
from dotenv import load_dotenv
from chaos_mesh.chaos_experiments import ChaosExperimentManager, PodKillException
from k8s.k8s_client import K8sClient
from monitoring.prometheus.prometheus_client import PrometheusClient
from .reward import RewardCalculator
from .state_builder import StateBuilder
from .config import TRAINING_CONFIG

class MicroserviceEnv(gym.Env):
    def __init__(self, deployment_name='nginx', namespace='default'):
        super().__init__()
        load_dotenv()
        self.max_replicas = TRAINING_CONFIG.get('max_replicas', 15)
        # Action space: 0=down, 1=nothing, 2=up
        self.action_space = spaces.Discrete(3)
        # Observation space: [cpu, mem, replicas, latency, rps]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 1, 0, -100], dtype=np.float32),
            high=np.array([500, 1, self.max_replicas, 5000, 100], dtype=np.float32),
            shape=(5,),
            dtype=np.float32
        )
        self.deployment_name = deployment_name
        self.namespace = namespace
        self.prom_client = PrometheusClient()
        self.metric_window = TRAINING_CONFIG.get('metric_window', '30s')
        self.action_interval = TRAINING_CONFIG.get('action_interval', 30)
        self.pod_counts = []
        self.steps = []
        self.current_step = 0
        self.max_steps = 200
        self.k8s_client = K8sClient(self.deployment_name, self.namespace)
        self.chaos_manager = ChaosExperimentManager(self.k8s_client.k8s_api, self.deployment_name, self.namespace)

    def reset(self, seed=None, options=None):
        """
        Reset the environment to an initial state.
        Waits for stabilization, scales pods to current count, and returns the initial state.
        """
        super().reset(seed=seed)
        time.sleep(self.action_interval)
        self._scale_pods(self._get_current_replicas())
        time.sleep(self.action_interval)
        state = self._get_state()
        self.current_step = 0
        return state, {}

    def step(self, action: int) -> tuple:
        """
        Take an action in the environment.
        Args:
            action: The action to take (0=down, 1=nothing, 2=up).
        Returns:
            Tuple of (new_state, reward, done, truncated, info)
        """
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
            self.chaos_manager.cleanup_chaos()
            # Inject chaos randomly if none are active
            if not self.chaos_manager.active_chaos_instances:
                self.chaos_manager.inject_chaos(self._wait_for_pods_ready)
            # Get new state after action and chaos
            new_state = self._get_state()
            # Print latency change if scaling occurred
            if replica_change != 0:
                latency_change = new_state[3] - state[3]
                print(f"Latency change: {latency_change:.2f}ms (from {state[3]:.2f} to {new_state[3]:.2f})", end=' ')
            # Calculate reward and check if episode is done
            reward, done = RewardCalculator.calculate_reward(
                new_state,
                self._get_annotations(),
                self.max_replicas
            )
            print(f'Reward: {reward:.4f}')
            # Track pod counts and steps for analysis
            self.current_step += 1
            self.steps.append(self.current_step)
            self.pod_counts.append(target_replica)
            # Check for max steps (truncate episode)
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
        except PodKillException as e:
            print(f"Pod kill exception: {e}, Reward: -50")
            state = self._get_state()
            return state, -50, True, False, {'error': 'All pods killed'}
        except KubernetesException as e:
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
        """Wait for the specified number of pods to be ready."""
        return self.k8s_client.wait_for_pods_ready(expected_replicas, timeout)

    def _scale_pods(self, replicas: int):
        """Scale the Kubernetes deployment to the specified number of replicas."""
        self.k8s_client.scale_deployment(replicas)

    def _get_current_replicas(self) -> int:
        """Get the current number of replicas for the deployment."""
        return self.k8s_client.get_current_replicas()

    def _get_annotations(self):
        """Get deployment annotations from Kubernetes."""
        return self.k8s_client.get_annotations()

    def _get_state(self) -> np.ndarray:
        """
        Query Prometheus and Kubernetes to build the current state observation.
        Returns:
            Numpy array representing the state.
        """
        try:
            cpu_usage_percent = self.prom_client.query(
                f'sum(rate(container_cpu_usage_seconds_total{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}}[1m])) * 100'
            )
            memory_bytes = self.prom_client.query(
                f'sum(container_memory_working_set_bytes{{namespace="{self.namespace}", pod=~"{self.deployment_name}-.*"}})'
            )
            p95_latency_ms = self.prom_client.query(
                f'histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{{reporter="destination", destination_workload="{self.deployment_name}"}}[5m])) by (le))'
            )
            rps = self.prom_client.query(
                f'sum(rate(istio_requests_total{{reporter="destination", destination_workload="{self.deployment_name}"}}[1m]))'
            )
            n_replicas = self._get_current_replicas()
            max_memory_per_pod = TRAINING_CONFIG.get('max_memory_per_pod', 512 * 1024 * 1024)
            current_state = StateBuilder.build_state(
                cpu_usage_percent,
                memory_bytes,
                n_replicas,
                p95_latency_ms,
                rps,
                max_memory_per_pod
            )
            return current_state
        except Exception as e:
            print(f"Error getting state: {str(e)}")
            return np.zeros(self.observation_space.shape, dtype=np.float32)

    def get_pod_history(self):
        """Return the history of pod counts and steps for analysis."""
        return self.steps, self.pod_counts
