# Copyright (c) 2019 Patrick Hart, Julian Bernhard,
# Klemens Esterle, Tobias Kessler
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

import gym
from gym.envs.registration import register

from bark_project.modules.runtime.commons.parameters import ParameterServer

from bark_ml.environments.blueprints.highway.highway import \
  ContinuousHighwayBlueprint, DiscreteHighwayBlueprint
from bark_ml.environments.blueprints.merging.merging import \
  ContinuousMergingBlueprint, DiscreteMergingBlueprint
from bark_ml.environments.single_agent_runtime import SingleAgentRuntime


# highway
class ContinuousHighwayGym(SingleAgentRuntime, gym.Env):
  def __init__(self):
    params = ParameterServer()
    cont_highway_bp = ContinuousHighwayBlueprint(params)
    SingleAgentRuntime.__init__(self,
      blueprint=cont_highway_bp, render=True)

class DiscreteHighwayGym(SingleAgentRuntime, gym.Env):
  def __init__(self):
    params = ParameterServer()
    discrete_highway_bp = DiscreteHighwayBlueprint(params)
    SingleAgentRuntime.__init__(self,
      blueprint=discrete_highway_bp, render=True)

# merging
class ContinuousMergingGym(SingleAgentRuntime, gym.Env):
  def __init__(self):
    params = ParameterServer()
    cont_merging_bp = ContinuousMergingBlueprint(params)
    SingleAgentRuntime.__init__(self,
      blueprint=cont_merging_bp, render=True)

class DiscreteMergingGym(SingleAgentRuntime, gym.Env):
  def __init__(self):
    params = ParameterServer()
    discrete_merging_bp = DiscreteMergingBlueprint(params)
    SingleAgentRuntime.__init__(self,
      blueprint=discrete_merging_bp, render=True)


# register gym envs
register(
  id='highway-v0',
  entry_point='bark_ml.environments.gym:ContinuousHighwayGym'
)
register(
  id='highway-v1',
  entry_point='bark_ml.environments.gym:DiscreteHighwayGym'
)
register(
  id='merging-v0',
  entry_point='bark_ml.environments.gym:ContinuousMergingGym'
)
register(
  id='merging-v1',
  entry_point='bark_ml.environments.gym:DiscreteMergingGym'
)