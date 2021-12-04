#!/usr/bin/env python
import sys
import traceback
import argparse
import time
import tensorflow as tf
from gameState import dsgym
from stable_baselines.ppo2 import PPO2
from stable_baselines.common.policies import MlpLstmPolicy, MlpPolicy, MlpLnLstmPolicy
from stable_baselines import logger
from stable_baselines.common.vec_env.dummy_vec_env import DummyVecEnv
from stable_baselines.common.vec_env.vec_normalize import VecNormalize

def train(num_timesteps,model_to_load):
    
    try:
        env = DummyVecEnv([dsgym])
        #env = VecNormalize(env)
        policy=MlpPolicy
        lr=3e-4

        model = PPO2(policy=policy, env=env, n_steps=256, nminibatches=1, lam=0.95, gamma=0.99, noptepochs=10,
                 ent_coef=0.01, learning_rate=linear_schedule(lr), cliprange=0.2)
        if model_to_load:
            env = DummyVecEnv([dsgym])
            #env = VecNormalize.load(model_to_load ,env)
            model = model.load(model_to_load)
            model.set_env(env)
            print("Loaded model from: ",model_to_load)
            model.set_learning_rate_func(linear_schedule_start_zero(lr))
        model.learn(total_timesteps=num_timesteps)
    except KeyboardInterrupt:
        print("Saving on keyinterrupt")
        model.save("D:/openAi/ppo2save/" + time.strftime("%Y_%m_%d-%H_%M_%S"))
        # quit
        sys.exit()
    except BaseException as error:
        model.save("D:/openAi/ppo2save/" + time.strftime("%Y_%m_%d-%H_%M_%S"))
        print('An exception occurred: {}'.format(error))
        traceback.print_exception(*sys.exc_info()) 
        sys.exit()
    model.save("D:/openAi/ppo2save/" + time.strftime("%Y_%m_%d-%H_%M_%S"))

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--load-dir", type=str, default=None,
                        help="directory to force load model from and continue training")
    logger.configure("D:/openAi/ppo2/"+time.strftime("%Y_%m_%d-%H_%M_%S"),["tensorboard","stdout"])
    args = parser.parse_args()
    train(num_timesteps=10000000,model_to_load=args.load_dir)

def linear_schedule(initial_value):
    """
    Linear learning rate schedule.
    :param initial_value: (float or str)
    :return: (function)
    """
    if isinstance(initial_value, str):
        initial_value = float(initial_value)

    def func(progress,update):
        """
        Progress will decrease from 1 (beginning) to 0
        :param progress: (float)
        :return: (float)
        """
        return progress * initial_value

    return func

def linear_schedule_start_zero(initial_value):
    """
    Linear learning rate schedule. Starting with a learning rate of 0 for the few updates to get steady adam params before continuing training (after loading)
    :param initial_value: (float or str)
    :return: (function)
    """
    if isinstance(initial_value, str):
        initial_value = float(initial_value)
    update_counter = 0

    def func(progress,update):
        """
        Progress will decrease from 1 (beginning) to 0
        :param progress: (float)
        :return: (float)
        """
        if(update < 5):
            print("Update_counter:",update)
            return 0
        return progress * initial_value

    return func


if __name__ == '__main__':
    main()
