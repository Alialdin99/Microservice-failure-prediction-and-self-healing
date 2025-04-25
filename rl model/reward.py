import numpy as np
class RewardCalculator:
    def calculate_reward(self, state, action, next_state):
        # Extract relevant metrics from states
        cpu_usage_percent = state["cpu_usage_percent"]
        memory = state["memory"]
        avg_request_latency = state["avg_request_latency"]
        request_error_rate = state["request_error_rate"]
        pod_restarts = state["pod_restarts"]
        pod_count = state["pod_count"]
        
        next_cpu_usage_percent = next_state["cpu_usage_percent"]
        next_memory = next_state["memory"]
        next_avg_request_latency = next_state["avg_request_latency"]
        next_request_error_rate = next_state["request_error_rate"]
        next_pod_restarts = next_state["pod_restarts"]
        next_pod_count = next_state["pod_count"]
        
        reward = 0
        
        # Reward for reducing pod restarts
        if next_pod_restarts < pod_restarts:
            reward += 2  # Reward for reducing pod restarts

        # Penalty for increasing pod restarts
        if next_pod_restarts > pod_restarts:
            reward -= 3  # Penalize if pod restarts increase

        # Reward for improving CPU usage (lower usage)
        if next_cpu_usage_percent < cpu_usage_percent:
            reward += 1  # Reward for reducing CPU usage

        # Penalty for high CPU usage
        if next_cpu_usage_percent > 80:  # Assuming 80% as a high threshold
            reward -= 2  # Penalize if CPU usage goes too high

        # Reward for reducing memory usage
        if next_memory < memory:
            reward += 1  # Reward for reducing memory usage

        # Penalty for excessive memory usage (e.g., above 80% of max capacity)
        if next_memory > 80:  # Assuming 80% as a high threshold
            reward -= 2  # Penalize for excessive memory usage

        # Reward for decreasing request error rate (improved reliability)
        if next_request_error_rate < request_error_rate:
            reward += 2  # Reward for decreasing request error rate

        # Penalty for high request error rate
        if next_request_error_rate > 0.05:  # Threshold for a high error rate (5%)
            reward -= 3  # Penalize for high error rates

        # Reward for reducing average request latency
        if next_avg_request_latency < avg_request_latency:
            reward += 1  # Reward for lowering latency

        # Penalty for high request latency (threshold: 500ms)
        if next_avg_request_latency > 500:  # Threshold of 500ms for latency
            reward -= 2  # Penalize for high latency

        # Reward for scaling pods efficiently
        if action == "scale_up" and next_pod_count > pod_count:
            if next_pod_count <= 10:  # Limit the scale-up to 10 pods to avoid over-scaling
                reward += 1  # Reward for scaling up when necessary

        if action == "scale_down" and next_pod_count < pod_count:
            if next_pod_count >= 2:  # Prevent scaling down too much
                reward += 1  # Reward for scaling down when necessary

        # Reward for maintaining pod count without issues
        if action == "do_nothing" and next_pod_count == pod_count:
            reward += 0.5  # Reward for stability when no scaling is needed

        return reward

    def _print_debug(self, optimal_pods, excess_pods, components, total_reward):
        """Print detailed reward breakdown"""
        print(f"\n{' Optimal Pods ':^20}{' Excess Pods ':^20}{' Total Reward ':^20}")
        print(f"{optimal_pods:^20}{excess_pods:^20}{total_reward:^20.2f}\n")
        
        print(f"{' Component ':<20}{' Value ':<15}{' Weighted ':>15}")
        print("-"*50)
        for name, value in components.items():
            print(f"{name:<20}{value/self.weights.get(name,1):<15.2f}{value:>15.2f}")
        print("="*50 + "\n")