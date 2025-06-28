"""Configuration parameters for training"""

# Training parameters
TRAINING_CONFIG = {
    "algorithm": "PPO",
    "learning_rate": 0.0003,
    "n_steps": 256,            # Keep 256 steps per update
    "batch_size": 64,          # Changed to 32 (must be a factor of n_steps * n_envs)
    "n_epochs": 10,            # Keep 10 epochs for good learning
    "gamma": 0.99,             # discount factor
    "gae_lambda": 0.95,        # factor for trade-off of bias vs variance for GAE
    "clip_range": 0.2,         # clipping parameter for PPO
    "ent_coef": 0.05,          # Keep high exploration
    "vf_coef": 0.5,            # value function coefficient
    "max_grad_norm": 0.5,      # maximum norm for gradient clipping
    "use_sde": False,          # use generalized State Dependent Exploration
    "sde_sample_freq": -1,     # sample a new noise matrix every n steps
    "target_kl": None,         # limit the KL divergence between updates
    "tensorboard_log": "./Results/tensorboard",  # log dir for tensorboard
    "create_eval_env": True,   # whether to create a second environment for evaluation
    "policy_kwargs": dict(
        net_arch=[dict(
            pi=[64, 64],       # Keep larger network for capacity
            vf=[64, 64]        # Keep larger network for capacity
        )]
    ),
}

# Training settings
TRAINING_SETTINGS = {
    "total_timesteps": 2000,    # Keep 2000 total timesteps
    "eval_freq": 256,          # Changed to match n_steps
    "n_eval_episodes": 5,      # Keep 5 evaluation episodes
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