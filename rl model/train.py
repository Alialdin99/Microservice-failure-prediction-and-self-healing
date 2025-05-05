import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.monitor import Monitor
from env import MicroserviceEnv
import wandb
from wandb.integration.sb3 import WandbCallback

# Initialize wandb for experiment tracking
wandb.init(
    project="microservice-rl",
    config={
        "algorithm": "PPO",
        "learning_rate": 0.0003,
        "n_steps": 2048,
        "batch_size": 64,
        "n_epochs": 10,
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
    best_model_save_path="./best_model",
    log_path="./logs/",
    eval_freq=1000,
    deterministic=True,
    render=False
)

# Create wandb callback
wandb_callback = WandbCallback(
    gradient_save_freq=100,
    model_save_path=f"models/{wandb.run.id}",
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
    tensorboard_log="./tensorboard/"
)

# Create directories if they don't exist
os.makedirs("./best_model", exist_ok=True)
os.makedirs("./logs", exist_ok=True)
os.makedirs("./tensorboard", exist_ok=True)
os.makedirs("./models", exist_ok=True)

# Train the model
total_timesteps = 100000  # Adjust based on your needs
model.learn(
    total_timesteps=total_timesteps,
    callback=[eval_callback, wandb_callback],
    progress_bar=True
)

# Save the final model
model.save("final_model")

# Close wandb
wandb.finish()