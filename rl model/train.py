from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from env import MicroserviceEnv

env = MicroserviceEnv()
    
# Verify environment
# check_env(env)

# Train with PPO
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    ent_coef=0.01,
    verbose=1,
    seed=42,
)

# Training loop
model.learn(total_timesteps=10000)
model.save("microservice_rl_agent")