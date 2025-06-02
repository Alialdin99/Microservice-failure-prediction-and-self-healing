from stable_baselines3.common.callbacks import BaseCallback
import matplotlib.pyplot as plt

class PodTrackingCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.pod_counts = []
        self.steps = []
        
    def _on_step(self):
        # Get the current number of pods from the environment
        current_pods = self.training_env.envs[0].env._get_current_pods()
        self.pod_counts.append(current_pods)
        self.steps.append(self.num_timesteps)
        return True
        
    def plot_pod_history(self, save_path='pod_scaling_history.png'):
        """Plot and save the pod scaling history"""
        plt.figure(figsize=(12, 6))
        plt.plot(self.steps, self.pod_counts, 'b-', label='Number of Pods')
        plt.xlabel('Steps')
        plt.ylabel('Number of Pods')
        plt.title('Pod Scaling Over Time')
        plt.grid(True)
        plt.legend()
        plt.savefig(save_path)
        plt.close()
        print(f"Plot has been saved as '{save_path}'") 