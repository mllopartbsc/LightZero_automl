import copy
from datetime import datetime
from typing import Union, Optional, Dict

from game import Game as MartisGame, MAX_LINES

import gymnasium as gym
import numpy as np
from ding.envs import BaseEnv, BaseEnvTimestep
from ding.envs import ObsPlusPrevActRewWrapper
from ding.torch_utils import to_ndarray
from ding.utils import ENV_REGISTRY
from easydict import EasyDict


@ENV_REGISTRY.register('martis_game_lightzero')
class MartisGameEnv(BaseEnv):
    """
    LightZero version of Marti's Game environment. Based on the classic Cartpole environment. This version uses discretized environment, in particular the decimal constant is entered by repeated presses of the arrow keys, much like one would set the time on a Casio wrist watch.
    """

    config = dict(
        # env_id (str): The name of the environment.
        env_id="MartisGame-v0",
        # replay_path (str): The path to save the replay video. If None, the replay will not be saved.
        # Only effective when env_manager.type is 'base'.
        replay_path=None,
    )

    @classmethod
    def default_config(cls: type) -> EasyDict:
        cfg = EasyDict(copy.deepcopy(cls.config))
        cfg.cfg_type = cls.__name__ + 'Dict'
        return cfg

    def my_space(self) -> gym.spaces.Space:
        SPACE_SHAPE = MAX_LINES * 64 # maybe should be (MAX_LINES, 64)
        return gym.spaces.MultiBinary(SPACE_SHAPE)
    
    def __init__(self, cfg: dict = {}) -> None:
        """
        Initialize the environment with a configuration dictionary. Sets up spaces for observations, actions, and rewards.
        """
        self._cfg = cfg
        self._init_flag = False
        self._continuous = False
        self._replay_path = cfg.replay_path
        self._observation_space = gym.spaces.MultiBinary(1280) 
        self._action_space = gym.spaces.Discrete(MartisGame.NUM_ACTIONS)
        self._action_space.seed(0)  # default seed
        self._reward_space = gym.spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)

        self.game = MartisGame()

    def reset(self) -> Dict[str, np.ndarray]:
        """
        Reset the environment. If it hasn't been initialized yet, this method also handles that. It also handles seeding
        if necessary. Returns the first observation.
        """

        self.game.reset()
        obs = self.game.state()

        # self._observation_space = self._env.observation_space
        self._observation_space = self.my_space()
        self._eval_episode_return = 0
        obs = to_ndarray(obs)

        action_mask = np.ones(self.action_space.n, 'int8')
        obs = {'observation': obs, 'action_mask': action_mask, 'to_play': -1}

        return obs

    def step(self, action: Union[int, np.ndarray]) -> BaseEnvTimestep:
        """
        Overview:
            Perform a step in the environment using the provided action, and return the next state of the environment.
            The next state is encapsulated in a BaseEnvTimestep object, which includes the new observation, reward,
            done flag, and info dictionary.
        Arguments:
            - action (:obj:`Union[int, np.ndarray]`): The action to be performed in the environment. If the action is
              a 1-dimensional numpy array, it is squeezed to a 0-dimension array.
        Returns:
            - timestep (:obj:`BaseEnvTimestep`): An object containing the new observation, reward, done flag,
              and info dictionary.
        .. note::
            - The cumulative reward (`_eval_episode_return`) is updated with the reward obtained in this step.
            - If the episode ends (done is True), the total reward for the episode is stored in the info dictionary
              under the key 'eval_episode_return'.
            - An action mask is created with ones, which represents the availability of each action in the action space.
            - Observations are returned in a dictionary format containing 'observation', 'action_mask', and 'to_play'.
        """
        if isinstance(action, np.ndarray) and action.shape == (1,):
            action = action.squeeze()  # 0-dim array

        obs, rew, terminated, truncated, info = self.game.step(action)
        done = terminated or truncated

        self._eval_episode_return += rew
        if done:
            info['eval_episode_return'] = self._eval_episode_return

        action_mask = np.ones(self.action_space.n, 'int8')
        obs = {'observation': obs, 'action_mask': action_mask, 'to_play': -1}

        return BaseEnvTimestep(obs, rew, done, info)

    def close(self) -> None:
        """
        Close the environment, and set the initialization flag to False.
        """
        if self._init_flag:
            # self._env.close()
            pass
        self._init_flag = False

    def seed(self, seed: int, dynamic_seed: bool = True) -> None:
        """
        Set the seed for the environment's random number generator. Can handle both static and dynamic seeding.
        """
        self._seed = seed
        self._dynamic_seed = dynamic_seed
        np.random.seed(self._seed)

    def enable_save_replay(self, replay_path: Optional[str] = None) -> None:
        """
        Enable the saving of replay videos. If no replay path is given, a default is used.
        """
        if replay_path is None:
            replay_path = './video'
        self._replay_path = replay_path

    def random_action(self) -> np.ndarray:
        """
         Generate a random action using the action space's sample method. Returns a numpy array containing the action.
         """
        random_action = self.action_space.sample()
        random_action = to_ndarray([random_action], dtype=np.int64)
        return random_action

    @property
    def observation_space(self) -> gym.spaces.Space:
        """
        Property to access the observation space of the environment.
        """
        return self._observation_space

    @property
    def action_space(self) -> gym.spaces.Space:
        """
        Property to access the action space of the environment.
        """
        return self._action_space

    @property
    def reward_space(self) -> gym.spaces.Space:
        """
        Property to access the reward space of the environment.
        """
        return self._reward_space

    def __repr__(self) -> str:
        """
        String representation of the environment.
        """
        return "LightZero MartisGame Env"
