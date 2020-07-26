import os
from pathlib import Path

from absl import app
from absl import flags

# BARK imports
from bark_project.bark.runtime.commons.parameters import ParameterServer
from bark.runtime.viewer.matplotlib_viewer import MPViewer
from bark.runtime.viewer.video_renderer import VideoRenderer

# BARK-ML imports
from bark_ml.environments.blueprints import ContinuousHighwayBlueprint, \
  ContinuousMergingBlueprint, ContinuousIntersectionBlueprint, GailMergingBlueprint
from bark_ml.environments.single_agent_runtime import SingleAgentRuntime
from bark_ml.library_wrappers.lib_tf2rl.tf2rl_wrapper import TF2RLWrapper
from bark_ml.library_wrappers.lib_tf2rl.agents.gail_agent import BehaviorGAILAgent
from bark_ml.library_wrappers.lib_tf2rl.runners.gail_runner import GAILRunner
from bark_ml.library_wrappers.lib_tf2rl.load_expert_trajectories import load_expert_trajectories


FLAGS = flags.FLAGS
flags.DEFINE_enum("mode",
                  "visualize",
                  ["train", "visualize", "evaluate"],
                  "Mode the configuration should be executed in.")

flags.DEFINE_string("train_out",
                  help="The absolute path to where the checkpoints and summaries are saved during training.",
                  # default=os.path.join(Path.home(), ".bark-ml/gail")
                  default=os.path.join(Path.home(), "")
                  )

flags.DEFINE_integer("gpu",
                  help="-1 for CPU, 0 for GPU",
                  default=0
                  )

flags.DEFINE_integer("subset_size",
                  help="Amount of expert trajectories to sample, < 0 for all",
                  default=-1
                  )

flags.DEFINE_string("expert_trajectories",
                    help="The absolute path to the dir where the expert trajectories are safed.",
                    default=None)

def run_configuration(argv):
  params = ParameterServer(filename="examples/example_params/gail_params.json")

  params["ML"]["GAILRunner"]["tf2rl"]["logdir"] = os.path.expanduser(FLAGS.train_out)
  params["ML"]["GAILRunner"]["tf2rl"]["model_dir"] = os.path.expanduser(FLAGS.train_out)
  if FLAGS.mode == 'train':
    params["ML"]["GAILRunner"]["tf2rl"]["logdir"] = os.path.join(params["ML"]["GAILRunner"]["tf2rl"]["logdir"], "logs")
    params["ML"]["GAILRunner"]["tf2rl"]["model_dir"] = os.path.join(params["ML"]["GAILRunner"]["tf2rl"]["model_dir"], "models")  

  Path(params["ML"]["GAILRunner"]["tf2rl"]["logdir"]).mkdir(exist_ok=True, parents=True)
  Path(params["ML"]["GAILRunner"]["tf2rl"]["model_dir"]).mkdir(exist_ok=True, parents=True)

  params["World"]["remove_agents_out_of_map"] = True
  params["ML"]["Settings"]["GPUUse"] = FLAGS.gpu

  # create environment
  bp = ContinuousMergingBlueprint(params,
                                  number_of_senarios=500,
                                  random_seed=0)
  env = SingleAgentRuntime(blueprint=bp,
                          render=False)

  # wrapped environment for compatibility with tf2rl
  wrapped_env = TF2RLWrapper(env, 
    normalize_features=params["ML"]["Settings"]["NormalizeFeatures"])

  # GAIL-agent
  gail_agent = BehaviorGAILAgent(environment=wrapped_env,
                               params=params)

  expert_trajectories, avg_trajectory_length, num_trajectories = load_expert_trajectories(FLAGS.expert_trajectories,
    normalize_features=params["ML"]["Settings"]["NormalizeFeatures"],
    env=env, # the unwrapped env has to be used, since that contains the unnormalized spaces.
    subset_size=FLAGS.subset_size
    ) 

  runner = GAILRunner(params=params,
                     environment=wrapped_env,
                     agent=gail_agent,
                     expert_trajs=expert_trajectories)

  if FLAGS.mode == "train":
    runner.Train()
  elif FLAGS.mode == "visualize":
    runner.Visualize(20)
  elif FLAGS.mode == "evaluate":
    runner.Evaluate(expert_trajectories, avg_trajectory_length, num_trajectories)
  
  # store all used params of the training
  # params.Save(os.path.join(FLAGS.train_out, "examples/example_params/gail_params.json"))


if __name__ == '__main__':
  flags.mark_flag_as_required("expert_trajectories")
  app.run(run_configuration)