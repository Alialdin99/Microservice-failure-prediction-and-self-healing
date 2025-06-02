"""Configuration parameters for training"""

# Training parameters
TRAINING_CONFIG = {
    "algorithm": "PPO",
    "learning_rate": 0.0003,
    "n_steps": 250,        # collect 1 step per update
    "batch_size": 50,     # batch_size must be a factor of n_steps * n_envs (250)
    "n_epochs": 4,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
}

# Training settings
TRAINING_SETTINGS = {
    "total_timesteps": 150,
    "eval_freq": 100,
    "n_eval_episodes": 5,
}

# Directory paths
PATHS = {
    "results_dir": "./Results",
    "best_model_dir": "./Results/best_model",
    "logs_dir": "./Results/logs",
    "tensorboard_dir": "./Results/tensorboard",
    "models_dir": "./Results/models",
    "pod_history_plot": "pod_scaling_history.png"
} 