
from gameState import dsgym
from stable_baselines.deepq import DQN,MlpPolicy
from stable_baselines import logger
from functools import partial
import time

def main():
    env = dsgym(isMultiDiscrete=False)
    policy = partial(MlpPolicy, dueling=True)
    logger.configure("D:/openAi/dqn/vordt/"+time.strftime("%Y_%m_%d-%H_%M_%S"),["tensorboard","stdout"])

    model = DQN(
        env=env,
        policy=policy,
        learning_rate=1e-4,
        buffer_size=50000,
        exploration_fraction=0.1,
        exploration_final_eps=0.01,
        train_freq=4,
        learning_starts=1000,
        target_network_update_freq=1000,
        gamma=0.99,
        prioritized_replay=bool(1),
        prioritized_replay_alpha=0.6,
    )
    model.learn(total_timesteps=int(1e6))

    env.close()


if __name__ == '__main__':
    main()
