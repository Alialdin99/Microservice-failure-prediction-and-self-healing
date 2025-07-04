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
        # Favor minimum r1 (i.e., minimum replicas) and 2000 rps per replica
        replicas = max(1, new_state[2])
        rps = new_state[4]
        latency = new_state[3]
        latencySoftConstraint = float(annotations.get('latencySoftConstraint', -1))
        latencyHardConstraint = float(annotations.get('latencyHardConstraint', -1))
        max_replicas = max(1, max_replicas)

        # r1: favor minimum replicas (maximize when replicas is 1)
        r1 = (max_replicas - replicas) / max_replicas

        # r2: favor 2000 rps per replica, 1 when exactly 2000, close to zero otherwise
        target_rps_per_replica = 2000.0
        rps_per_replica = rps / replicas if replicas > 0 else 0
        if rps_per_replica < target_rps_per_replica and replicas == 1:
            r2 = 1
        else:
            # Use a sharp Gaussian centered at 2000
            r2 = np.exp(-((rps_per_replica - target_rps_per_replica) ** 2) / (2 * (100 ** 2)))

        # r3: latency constraints
        r3 = 0
        terminated = False
        if latencySoftConstraint != -1 and latencyHardConstraint != -1:
            if latency > latencyHardConstraint:
                r3 = -1
                terminated = True
            elif latency > latencySoftConstraint:
                r3 = 1.0 - (latency - latencySoftConstraint) / (latencyHardConstraint - latencySoftConstraint)
            else:
                r3 = 1

        # Combine rewards: favor min replicas, target rps/replica, and latency
        reward = 0.4 * r1 + 0.4 * r2 + 0.2 * r3
        return reward, terminated