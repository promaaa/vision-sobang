"""Export a policy trained with --official to ONNX, in the same form as BHL policy_biped_25hz_a.onnx.

Usage: python export_onnx.py <run_dir>     -> <run_dir>/policy.onnx
Input "obs" float32 [1, 45], output "actions" float32 [1, 12], opset 11, IR 6 (as the BHL file).
The observation normaliser is folded into the first layer, so the ONNX takes the raw BHL observation.
The output is the mean action (no sampling). The script checks the ONNX against the JAX policy.
"""

import pickle
import sys

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

run_dir = sys.argv[1]
with open(f"{run_dir}/params_latest.pkl", "rb") as f:
  params = pickle.load(f)
norm, pol = params[0], params[1]["params"]
mean, std = np.asarray(norm.mean["state"], np.float64), np.asarray(norm.std["state"], np.float64)
assert mean.shape == (45,), "not an --official run: the policy input is not 45 values"
# Brax policy with a learned scalar std: MLP_0 (hidden layers, all activated) then Dense_0 (action mean).
layers = [pol["MLP_0"][f"hidden_{i}"] for i in range(len(pol["MLP_0"]))] + [pol["Dense_0"]]
n = len(layers)
Ws = [np.asarray(l["kernel"], np.float64) for l in layers]
bs = [np.asarray(l["bias"], np.float64) for l in layers]
bs[0] = bs[0] - (mean / std) @ Ws[0]  # fold (obs - mean) / std into layer 0
Ws[0] = Ws[0] / std[:, None]

nodes, inits, x = [], [], "obs"
for i, (W, b) in enumerate(zip(Ws, bs)):
  inits += [numpy_helper.from_array(W.astype(np.float32), f"W{i}"), numpy_helper.from_array(b.astype(np.float32), f"b{i}")]
  last = i == n - 1
  nodes.append(helper.make_node("Gemm", [x, f"W{i}", f"b{i}"], ["actions" if last else f"z{i}"]))
  if not last:  # Brax default activation: swish(z) = z * sigmoid(z)
    nodes += [helper.make_node("Sigmoid", [f"z{i}"], [f"s{i}"]), helper.make_node("Mul", [f"z{i}", f"s{i}"], [f"h{i}"])]
    x = f"h{i}"
graph = helper.make_graph(nodes, "bhl_payload_policy",
                          [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, 45])],
                          [helper.make_tensor_value_info("actions", TensorProto.FLOAT, [1, 12])], inits)
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 11)], producer_name="sim/rl/export_onnx.py")
model.ir_version = 6
onnx.checker.check_model(model)
onnx.save(model, f"{run_dir}/policy.onnx")

# Check: the ONNX gives the same action as the JAX policy (on observations like the real ones).
import jax  # pylint: disable=g-import-not-at-top
import onnxruntime as ort
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks

net = ppo_networks.make_ppo_networks(
    {"state": (45,), "privileged_state": tuple(norm.mean["privileged_state"].shape)}, 12,
    preprocess_observations_fn=running_statistics.normalize, policy_hidden_layer_sizes=(512, 256, 128),
    value_hidden_layer_sizes=(512, 256, 128), policy_obs_key="state", value_obs_key="privileged_state",
    distribution_type="normal")
policy = ppo_networks.make_inference_fn(net)(params, deterministic=True)
sess = ort.InferenceSession(f"{run_dir}/policy.onnx", providers=["CPUExecutionProvider"])
rng = np.random.default_rng(0)
worst = 0.0
for _ in range(50):
  obs = (mean + std * rng.standard_normal(45)).astype(np.float32)[None]
  a_onnx = sess.run(None, {"obs": obs})[0]
  a_jax = np.asarray(policy({"state": obs[0], "privileged_state": np.zeros(norm.mean["privileged_state"].shape, np.float32)}, jax.random.PRNGKey(0))[0])
  worst = max(worst, float(np.abs(a_onnx[0] - a_jax).max()))
assert worst < 1e-3, f"ONNX and JAX differ by {worst}"
print(f"wrote {run_dir}/policy.onnx; max difference to JAX {worst:.2e}")
