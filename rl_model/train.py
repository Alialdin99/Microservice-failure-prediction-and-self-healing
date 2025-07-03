import os
import wandb
from .env import MicroserviceEnv
from stable_baselines3 import PPO
from wandb.integration.sb3 import WandbCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

from .callbacks import PodTrackingCallback
from .config import TRAINING_CONFIG, TRAINING_SETTINGS, PATHS

def setup_directories():
    """Create necessary directories if they don't exist"""
    for path in PATHS.values():
        if path.endswith(('.png', '.zip')):
            continue
        os.makedirs(path, exist_ok=True)

def create_environment():
    """Create and wrap the environment"""
    env = MicroserviceEnv()
    env = Monitor(env)
    return DummyVecEnv([lambda: env])

def create_callbacks(env, wandb_run):
    """Create all necessary callbacks"""
    eval_callback = EvalCallback(
        env,
        best_model_save_path=PATHS["best_model_dir"],
        log_path=PATHS["logs_dir"],
        eval_freq=TRAINING_SETTINGS["eval_freq"],
        deterministic=True,
        render=False,
        n_eval_episodes=TRAINING_SETTINGS["n_eval_episodes"],
    )

    wandb_callback = WandbCallback(
        gradient_save_freq=50,
        model_save_path=f"{PATHS['models_dir']}/{wandb_run.id}",
        verbose=2,
    )

    pod_callback = PodTrackingCallback()

    return [eval_callback, wandb_callback, pod_callback]

def main():
    # Initialize wandb
    wandb.init(
        project="microservice-rl",
        dir=PATHS["results_dir"],
        config=TRAINING_CONFIG
    )

    # Setup directories
    setup_directories()

    # Create environments
    env = create_environment()
    eval_env = create_environment()

    # Create callbacks
    callbacks = create_callbacks(eval_env, wandb.run)

    # Initialize the model
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=wandb.config.learning_rate,
        n_steps=wandb.config.n_steps,
        batch_size=wandb.config.batch_size,
        n_epochs=wandb.config.n_epochs,
        gamma=wandb.config.gamma,
        gae_lambda=wandb.config.gae_lambda,
        clip_range=wandb.config.clip_range,
        ent_coef=wandb.config.ent_coef,
        verbose=1,
        tensorboard_log=PATHS["tensorboard_dir"],
        device='cpu'  # Force CPU usage to avoid CUDA warning
    )

    # Train the model
    model.learn(
        total_timesteps=TRAINING_SETTINGS["total_timesteps"],
        callback=callbacks,
        progress_bar=True
    )
    print("Training done!")

    # Save the final model
    model.save("final_model.zip")

    # Plot pod scaling history
    pod_callback = next(cb for cb in callbacks if isinstance(cb, PodTrackingCallback))
    pod_callback.plot_pod_history(PATHS["pod_history_plot"])

    # Close wandb
    wandb.finish()

if __name__ == "__main__":
    main()