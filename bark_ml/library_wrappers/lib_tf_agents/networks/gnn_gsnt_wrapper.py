# Copyright (c) 2020 fortiss GmbH
#
# Authors: Patrick Hart
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

import logging
import tensorflow as tf
from enum import Enum
from graph_nets import modules
from graph_nets import utils_tf
from graph_nets import utils_np
from graph_nets.graphs import GraphsTuple
import sonnet as snt

# bark-ml
from bark.runtime.commons.parameters import ParameterServer
from bark_ml.observers.graph_observer import GraphObserver
from bark_ml.library_wrappers.lib_tf_agents.networks.gnn_wrapper import GNNWrapper

NUM_LAYERS = 2  # Hard-code number of layers in the edge/node/global models.
LATENT_SIZE = 40  # Hard-code latent layer sizes for demos.


def make_mlp_model(layer_config=None):
  """Instantiates a new MLP, followed by LayerNorm.
  The parameters of each new MLP are not shared with others generated by
  this function.
  Returns:
    A Sonnet module which contains the MLP and LayerNorm.
  """
  lc = layer_config or [64, 32]
  return snt.Sequential([
      snt.nets.MLP(lc, activate_final=True, with_bias=True),
  ])

class MLPGraphNetwork(snt.Module):
  """GraphNetwork with MLP edge, node, and global models."""
  def __init__(self,
               edge_block_opt,
               node_block_opt, 
               global_block_opt,
               name="MLPGraphNetwork"):
    super(MLPGraphNetwork, self).__init__(name=name)
    self._network = modules.GraphNetwork(
      make_mlp_model,
      make_mlp_model,
      make_mlp_model,
      edge_block_opt=edge_block_opt,
      node_block_opt=node_block_opt,
      global_block_opt=global_block_opt)

  def __call__(self, inputs):
    return self._network(inputs)


class GSNTWrapper(GNNWrapper):
  """
  Implements a graph lib.
  """

  def __init__(self,
               params=ParameterServer(),
               name='GNST',
               output_dtype=tf.float32):
    """
    Initializes a GSNTWrapper instance.

    Args:
    params: A `ParameterServer` instance containing the parameters
      to configure the GNN.
    graph_dims: A tuple containing the three elements
      (num_nodes, len_node_features, len_edge_features) of the input graph.
      Needed to properly convert observations back into a graph structure 
      that can be processed by the GNN.
    name: Name of the instance.
    output_dtype: The dtype to which the GNN output is casted.
    """
    super(GSNTWrapper, self).__init__(
      params=params,
      name=name,
      output_dtype=output_dtype)
    self._num_message_passing_layers = params["ML"]["GSNT"][
      "NumMessagePassingLayers", "Number of message passing layers", 2]
    self._embedding_size = params["ML"]["GSNT"][
      "EmbeddingSize", "Embedding size of nodes", 32]
    # self._activation_func = params["ML"]["GAT"][
    #   "Activation", "Activation function", "elu"]
    # self._num_attn_heads = params["ML"]["GAT"][
    #   "NumAttnHeads", "Number of attention heads to be used", 4]
    # self._dropout_rate = params["ML"]["GAT"][
    #   "DropoutRate", "", 0.]
    self._layers = []
    # initialize network & call func
    self._init_network()
    self._call_func = self._init_call_func
    
  def _init_network(self):
    edge_block_opt = {
      "use_edges": True,
      "use_receiver_nodes": True,
      "use_sender_nodes": True,
      "use_globals": False
    }
    node_block_opt = {
      "use_received_edges": True,
      "use_nodes": True,
      "use_globals": False
    }
    self._gnn_core_0 = MLPGraphNetwork(
      edge_block_opt, node_block_opt, global_block_opt=None)
    self._gnn_core_1 = MLPGraphNetwork(
      edge_block_opt, node_block_opt, global_block_opt=None)

  @tf.function
  def _init_call_func(self, observations, training=False):
    """Graph nets implementation"""
    # print("gsnt", observations)
    embeddings, adj_matrix, _, edge_features = GraphObserver.graph(
      observations=observations, 
      graph_dims=self._graph_dims,
      dense=True)
    
    batch_size = tf.shape(observations)[0]
    input_graph = GraphsTuple(
      nodes=tf.cast(embeddings, tf.float32),  # validate
      edges=tf.cast(edge_features, tf.float32),  # validate
      globals=tf.cast(tf.tile([[0]], [batch_size, 1]), tf.float32),
      receivers=tf.cast(adj_matrix[:, 1], tf.int32),  # validate
      senders=tf.cast(adj_matrix[:, 0], tf.int32),  # validate
      n_node=tf.tile([5], [batch_size]),  # change
      n_edge=tf.tile([25], [batch_size]))  # change

    out = self._gnn_core_0(input_graph)
    out = self._gnn_core_1(out)
    
    # validate
    node_values = tf.reshape(out.nodes, [batch_size, -1, self._embedding_size])
    return node_values

