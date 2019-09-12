import tensorflow as tf

# tfa
from tf_agents.networks import actor_distribution_network
from tf_agents.networks import normal_projection_network
from tf_agents.agents.ddpg import critic_network
from tf_agents.policies import greedy_policy

from tf_agents.agents.sac import sac_agent
from tf_agents.replay_buffers import tf_uniform_replay_buffer
from tf_agents.utils.common import Checkpointer

from src.agents.tfa_agent import TFAAgent

class SACAgent(TFAAgent):
  """SAC Agent
  """
  def __init__(self,
               environment=None,
               replay_buffer=None,
               checkpointer=None,
               dataset=None,
               params=None):
    TFAAgent.__init__(self,
                      environment=environment,
                      params=params)
    self._agent = self.get_agent(environment, params)
    self._env = environment
    self._replay_buffer = self.get_replay_buffer()
    self._dataset = self.get_dataset()
    self._collect_policy = self.get_collect_policy()
    self._eval_policy = self.get_eval_policy()
    self._ckpt = tf.train.Checkpoint(step=tf.Variable(0, dtype=tf.int64),
                                     agent=self._agent)

  def get_agent(self, env, params):
    """Returns a TensorFlow SAC-Agent
    
    Arguments:
        env {TFAPyEnvironment} -- Tensorflow-Agents PyEnvironment
        params {ParameterServer} -- ParameterServer from BARK
    
    Returns:
        agent -- tf-agent
    """
    def _normal_projection_net(action_spec, init_means_output_factor=0.1):
      return normal_projection_network.NormalProjectionNetwork(
        action_spec,
        mean_transform=None,
        state_dependent_std=True,
        init_means_output_factor=init_means_output_factor,
        std_transform=sac_agent.std_clip_transform,
        scale_distribution=True)

    # actor network
    actor_net = actor_distribution_network.ActorDistributionNetwork(
        env.observation_spec(),
        env.action_spec(),
        fc_layer_params=tuple(
          self._params["ML"]["SACAgent"]["actor_fc_layer_params"]),
        continuous_projection_net=_normal_projection_net)

    # critic network
    critic_net = critic_network.CriticNetwork(
      (env.observation_spec(), env.action_spec()),
      observation_fc_layer_params=None,
      action_fc_layer_params=None,
      joint_fc_layer_params=tuple(
        self._params["ML"]["SACAgent"]["critic_joint_fc_layer_params"]))
    
    # agent
    tf_agent = sac_agent.SacAgent(
      env.time_step_spec(),
      env.action_spec(),
      actor_network=actor_net,
      critic_network=critic_net,
      actor_optimizer=tf.compat.v1.train.AdamOptimizer(
          learning_rate=self._params["ML"]["SACAgent"]["actor_learning_rate"]),
      critic_optimizer=tf.compat.v1.train.AdamOptimizer(
          learning_rate=self._params["ML"]["SACAgent"]["critic_learning_rate"]),
      alpha_optimizer=tf.compat.v1.train.AdamOptimizer(
          learning_rate=self._params["ML"]["SACAgent"]["alpha_learning_rate"]),
      target_update_tau=self._params["ML"]["SACAgent"]["target_update_tau"],
      target_update_period=self._params["ML"]["SACAgent"]["target_update_period"],
      td_errors_loss_fn=tf.compat.v1.losses.mean_squared_error,
      gamma=self._params["ML"]["SACAgent"]["gamma"],
      reward_scale_factor=self._params["ML"]["SACAgent"]["reward_scale_factor"],
      gradient_clipping=self._params["ML"]["SACAgent"]["gradient_clipping"],
      train_step_counter=self._ckpt.step,
      name=self._params["ML"]["SACAgent"]["agent_name"],
      debug_summaries=self._params["ML"]["SACAgent"]["debug_summaries"])
    tf_agent.initialize()
    return tf_agent

  def get_replay_buffer(self):
    """Replay buffer
    
    Returns:
        ReplayBuffer -- tf-agents replay buffer
    """
    return tf_uniform_replay_buffer.TFUniformReplayBuffer(
      data_spec=self._agent.collect_data_spec,
      batch_size=self._env.batch_size,
      max_length=self._params["ML"]["SACAgent"]["replay_buffer_capacity"])

  def get_dataset(self):
    """Dataset generated from the replay buffer
    
    Returns:
        dataset -- subset of experiences from the replay buffer
    """
    dataset = self._replay_buffer.as_dataset(
      num_parallel_calls=self._params["ML"]["SACAgent"]["parallel_buffer_calls"],
      sample_batch_size=self._params["ML"]["SACAgent"]["batch_size"],
      num_steps=self._params["ML"]["SACAgent"]["buffer_num_steps"]) \
        .prefetch(self._params["ML"]["SACAgent"]["buffer_prefetch"])
    return dataset

  def get_collect_policy(self):
    """Novel collection policy from the agent
    
    Returns:
        CollectPolicy -- Samples from the agent's distribution
    """
    return self._agent.collect_policy

  def get_eval_policy(self):
    """Returns a greedy policy from the agent
    
    Returns:
        GreedyPolicy -- Always returns best suitable action
    """
    return greedy_policy.GreedyPolicy(self._agent.policy)

  def reset(self):
    pass

  @property
  def collect_policy(self):
    return self._collect_policy

  @property
  def eval_policy(self):
    return self._eval_policy