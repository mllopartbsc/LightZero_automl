from easydict import EasyDict
from game import Game as MartisGame, MAX_LINES

# ==============================================================
# begin of the most frequently changed config specified by the user
# ==============================================================
collector_env_num = 8
n_episode = 8
evaluator_env_num = 5
num_simulations = 25
update_per_collect = 50
batch_size = 256
max_env_step = int(1e5)
reanalyze_ratio = 0
# ==============================================================
# end of the most frequently changed config specified by the user
# ==============================================================

martis_game_stochastic_muzero_config = dict(
    exp_name=f'data_stochastic_mz_ctree/martis_game_stochastic_muzero_ns{num_simulations}_upc{update_per_collect}_rr{reanalyze_ratio}_seed0',
    env=dict(
        env_id='MartisGame-v0',
        continuous=False,
        manually_discretization=False,
        collector_env_num=collector_env_num,
        evaluator_env_num=evaluator_env_num,
        n_evaluator_episode=evaluator_env_num,
        manager=dict(shared_memory=False, ),
    ),
    policy=dict(
        model=dict(
            observation_shape=MAX_LINES * 64, # Would (MAX_LINES, 64) or (3, 7, 62) be better? -- No, apparently this must be an int, not a tuple. Perhaps this has something to do with the observation space having been changed from Box to MultiBinary?
            action_space_size=MartisGame.action_space_size,
            chance_space_size=2,
            model_type='mlp',
            lstm_hidden_size=128,
            latent_state_dim=128,
            self_supervised_learning_loss=True,  # NOTE: default is False.
            discrete_action_encoding_type='one_hot',
            norm_type='BN', 
        ),
        mcts_ctree=True,
        cuda=True,
        env_type='not_board_games',
        game_segment_length=50,
        update_per_collect=update_per_collect,
        batch_size=batch_size,
        optim_type='Adam',
        lr_piecewise_constant_decay=False,
        learning_rate=0.003,
        ssl_loss_weight=2,  # NOTE: default is 0.
        num_simulations=num_simulations,
        reanalyze_ratio=reanalyze_ratio,
        n_episode=n_episode,
        eval_freq=int(2e2),
        replay_buffer_size=int(1e6),
        collector_env_num=collector_env_num,
        evaluator_env_num=evaluator_env_num,
    ),
)

martis_game_stochastic_muzero_config = EasyDict(martis_game_stochastic_muzero_config)
main_config = martis_game_stochastic_muzero_config

martis_game_stochastic_muzero_create_config = dict(
    env=dict(
        type='martis_game_lightzero',
        import_names=['zoo.assembly.martis_game.envs.martis_game_lightzero_env'],
    ),
    env_manager=dict(type='subprocess'),
    policy=dict(
        type='stochastic_muzero',
        import_names=['lzero.policy.stochastic_muzero'],
    ),
)
martis_game_stochastic_muzero_create_config = EasyDict(martis_game_stochastic_muzero_create_config)
create_config = martis_game_stochastic_muzero_create_config

if __name__ == "__main__":
    from lzero.entry import train_muzero
    train_muzero([main_config, create_config], seed=0, max_env_step=max_env_step)
