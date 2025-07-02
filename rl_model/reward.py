from typing import Tuple
import numpy as np

class RewardCalculator:
    """
    Calculates the reward and termination condition for the environment.
    """
    @staticmethod
    def calculate_reward(new_state: np.ndarray, annotations: dict, max_replicas: int) -> Tuple[float, bool]:
        """
        Calculate the reward and whether the episode should terminate.
        Args:
            new_state: The new state as a numpy array.
            annotations: Deployment annotations dict.
            max_replicas: Maximum allowed replicas.
        Returns:
            Tuple of (reward, terminated)
        """
        r1 = (max_replicas - new_state[2]) / max_replicas
        r2 = 0
        terminated = False
        latency = new_state[3]
        latencySoftConstraint = float(annotations.get('latencySoftConstraint', -1))
        latencyHardConstraint = float(annotations.get('latencyHardConstraint', -1))
        if latencySoftConstraint != -1 and latencyHardConstraint != -1:
            if latency > latencyHardConstraint:
                r2 = -1
                terminated = True
            elif latency > latencySoftConstraint:
                r2 = 1.0 - (latency - latencySoftConstraint) / (latencyHardConstraint - latencySoftConstraint)
            else:
                r2 = 1
        reward = 0.3 * r1 + 0.7 * r2
        return reward, terminated 