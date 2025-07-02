from typing import Any
import numpy as np

class StateBuilder:
    """
    Builds the observation/state for the environment.
    """
    @staticmethod
    def build_state(
        cpu_usage_percent: float,
        memory_bytes: float,
        n_replicas: int,
        p95_latency_ms: float,
        rps: float,
        max_memory_per_pod: int = 512 * 1024 * 1024
    ) -> np.ndarray:
        """
        Assemble the state vector for the environment.
        Args:
            cpu_usage_percent: CPU usage in percent.
            memory_bytes: Total memory usage in bytes.
            n_replicas: Number of replicas.
            p95_latency_ms: 95th percentile latency in ms.
            rps: Requests per second.
            max_memory_per_pod: Max memory per pod in bytes.
        Returns:
            Numpy array representing the state.
        """
        total_max_memory = max_memory_per_pod * n_replicas
        memory_normalized = memory_bytes / total_max_memory if total_max_memory > 0 else 0.0
        return np.array([
            cpu_usage_percent,
            memory_normalized,
            n_replicas,
            p95_latency_ms,
            rps
        ], dtype=np.float32) 