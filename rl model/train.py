import os
import wandb
import numpy as np
from env import MicroserviceEnv
from stable_baselines3 import PPO
from wandb.integration.sb3 import WandbCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

# Initialize wandb for experiment tracking
wandb.init(
    project="microservice-rl",
    dir="./Results",
    config={
        "algorithm": "PPO",
        "learning_rate": 0.0003,
        "n_steps": 250,       # collect 1 step per update (to match total_timesteps)
        "batch_size": 64,    # batch_size must be <= n_steps
        "n_epochs": 4,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "ent_coef": 0.01,
    }
)

# Create and wrap the environment
env = MicroserviceEnv()
env = Monitor(env)
env = DummyVecEnv([lambda: env])

# Create evaluation environment
eval_env = MicroserviceEnv()
eval_env = Monitor(eval_env)
eval_env = DummyVecEnv([lambda: eval_env])

# Create evaluation callback
eval_callback = EvalCallback(
    eval_env,
    best_model_save_path="./Results/best_model",
    log_path="./Results/logs/",
    eval_freq=100,            # Evaluate every 1 step (same as total_timesteps)
    deterministic=True,
    render=False,
    n_eval_episodes=5,
)

# Create wandb callback
wandb_callback = WandbCallback(
    gradient_save_freq=50,    # Save gradient info every 50 steps
    model_save_path=f"./Results/models/{wandb.run.id}",
    verbose=2,
)

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
    tensorboard_log="./Results/tensorboard/"
)

# Create directories if they don't exist
os.makedirs("./Results/best_model", exist_ok=True)
os.makedirs("./Results/logs", exist_ok=True)
os.makedirs("./Results/tensorboard", exist_ok=True)
os.makedirs("./Results/models", exist_ok=True)

# Train the model: run for 1 step total, then stop
model.learn(
    total_timesteps=1000,
    callback=[eval_callback, wandb_callback],
    progress_bar=True
)
print("Training done!")

# Save the final model
model.save("final_model.zip")

# Close wandb
wandb.finish()