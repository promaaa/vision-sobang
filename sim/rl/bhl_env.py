"""Berkeley Humanoid Lite biped joystick env with a torso payload (MuJoCo Playground / MJX).

Reuses Playground's Berkeley Humanoid joystick env (rewards, observations, pushes)
and only swaps the robot model, joint names and a few settings taken from the
official BHL Isaac Lab config (25 Hz control, action scale 0.25, PD 20/2, 6 Nm).

Run `python bhl_env.py` for the stand check: default pose + zero action for 1 s.
"""

import os

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from mujoco import mjx

from mujoco_playground._src import mjx_env
from mujoco_playground._src.locomotion.berkeley_humanoid import joystick as bh_joystick

XML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bhl_biped_payload.xml")
LEGS = ["hip_roll", "hip_yaw", "hip_pitch", "knee_pitch", "ankle_pitch", "ankle_roll"]


def default_config():
  c = bh_joystick.default_config()
  c.ctrl_dt = 0.04  # 25 Hz, as the official BHL policy.
  c.sim_dt = 0.005  # 200 Hz, as the official BHL sim.
  c.episode_length = 500  # 20 s.
  # Official BHL uses 0.25 with unbounded actions. Brax PPO squashes actions to [-1, 1] with tanh,
  # so 0.25 limits joint targets to +-0.25 rad around the default pose. Playground uses 0.5.
  c.action_scale = 0.5
  c.lin_vel_x = [-0.5, 0.5]
  c.lin_vel_y = [-0.25, 0.25]
  c.ang_vel_yaw = [-1.0, 1.0]
  c.reward_config.tracking_sigma = 0.1
  c.reward_config.max_foot_height = 0.08
  c.push_config.magnitude_range = [0.1, 1.0]
  c.naconmax = 16 * 8192
  c.njmax = 100
  c.effort_limit = 6.0  # Nm, official BHL Isaac Lab config (the MJCF motors allow 20 Nm)
  c.payload_max = 2.5  # kg, training payload range is U(0, payload_max)
  c.payload_com_shift = 0.03  # m, training payload CoM shift is U(-x, x) on each axis
  c.knee_limit = 0.0  # rad, upper knee limit; 0 keeps the MJCF value (2.44 rad)
  return c


class BHLJoystick(bh_joystick.Joystick):
  """Same task as Playground's BerkeleyHumanoidJoystickFlatTerrain, BHL robot."""

  def __init__(self, config=None, config_overrides=None):
    mjx_env.MjxEnv.__init__(self, config or default_config(), config_overrides)
    self._mj_model = mujoco.MjModel.from_xml_path(XML)
    self._mj_model.opt.timestep = self.sim_dt
    self._mj_model.actuator_forcerange[:] = [-self._config.effort_limit, self._config.effort_limit]
    if self._config.knee_limit:  # e.g. 1.4 rad so the shank clears the backpack (cad/backpack/README.md)
      for side in ("left", "right"):
        name = f"leg_{side}_knee_pitch_joint"
        self._mj_model.jnt_range[self._mj_model.joint(name).id, 1] = self._config.knee_limit
        self._mj_model.actuator_ctrlrange[self._mj_model.actuator(name).id, 1] = self._config.knee_limit
    self._xml_path = XML
    self.update_mjx_model()
    self._post_init()

  def update_mjx_model(self):
    """Copy mj_model to the GPU. Call again after you edit mj_model (e.g. payload mass)."""
    m = mjx.put_model(self._mj_model, impl=self._config.impl)
    if self._config.impl == "warp":  # silence per-step "solver iterations limit" prints
      m = m.replace(opt=m.opt.replace(_impl=m.opt._impl.replace(warn_overflow=0)))
    self._mjx_model = m

  def _post_init(self) -> None:
    m = self._mj_model
    self._init_q = jp.array(m.keyframe("home").qpos)
    self._default_pose = jp.array(m.keyframe("home").qpos[7:])
    self._lowers, self._uppers = m.jnt_range[1:].T
    c = (self._lowers + self._uppers) / 2
    r = self._uppers - self._lowers
    self._soft_lowers = c - 0.5 * r * self._config.soft_joint_pos_limit_factor
    self._soft_uppers = c + 0.5 * r * self._config.soft_joint_pos_limit_factor

    jid = lambda side, j: m.joint(f"leg_{side}_{j}_joint").qposadr[0] - 7
    self._hip_indices = jp.array([jid(s, j) for s in ("left", "right") for j in ("hip_yaw", "hip_roll")])
    self._knee_indices = jp.array([jid(s, "knee_pitch") for s in ("left", "right")])
    # Joint order per leg is the same as Berkeley Humanoid: roll/yaw, pitch, knee, ankle x2.
    self._weights = jp.array([1.0, 1.0, 0.01, 0.01, 1.0, 1.0] * 2)

    self._torso_body_id = m.body("base").id
    self._torso_mass = m.body_subtreemass[self._torso_body_id]
    self._site_id = m.site("imu").id
    self._feet_site_id = np.array([m.site(n).id for n in ("l_foot", "r_foot")])
    self._floor_geom_id = m.geom("floor").id
    self._feet_geom_id = np.array([m.geom(n).id for n in ("l_foot1", "r_foot1")])
    self._foot_linvel_sensor_adr = jp.array([
        list(range(m.sensor_adr[m.sensor(f"{s}_global_linvel").id],
                   m.sensor_adr[m.sensor(f"{s}_global_linvel").id] + 3))
        for s in ("l_foot", "r_foot")
    ])
    ns = self._config.noise_config.scales
    self._qpos_noise_scale = jp.array([ns.hip_pos] * 3 + [ns.kfe_pos, ns.ffe_pos, ns.faa_pos] * 1 + [ns.hip_pos] * 3 + [ns.kfe_pos, ns.ffe_pos, ns.faa_pos])
    self._feet_floor_found_sensor = [m.sensor(f"{g}_floor_found").id for g in ("l_foot1", "r_foot1")]

  def _get_termination(self, data):
    # Official BHL: terminate when the base tilts more than 0.78 rad.
    fall = self.get_gravity(data)[-1] < np.cos(0.78)
    return fall | jp.isnan(data.qpos).any() | jp.isnan(data.qvel).any()


def domain_randomize(model: mjx.Model, rng: jax.Array, mj_model: mujoco.MjModel = None,
                     payload_max: float = 2.5, com_shift: float = 0.03):
  """Playground BH randomisation + payload mass U(0, payload_max) kg, CoM shift U(+-com_shift), PD gain scale U(0.8, 1.2)."""
  mj_model = mj_model or mujoco.MjModel.from_xml_path(XML)
  floor = mj_model.geom("floor").id
  pay = mj_model.body("payload").id
  pay_m0 = mj_model.body_mass[pay]

  @jax.vmap
  def rand(rng):
    k = jax.random.split(rng, 9)
    friction = model.geom_friction.at[floor, 0].set(jax.random.uniform(k[0], minval=0.4, maxval=1.0))
    frictionloss = model.dof_frictionloss.at[6:].multiply(jax.random.uniform(k[1], (12,), minval=0.9, maxval=1.1))
    armature = model.dof_armature.at[6:].multiply(jax.random.uniform(k[2], (12,), minval=1.0, maxval=1.05))
    body_mass = model.body_mass * jax.random.uniform(k[3], (model.nbody,), minval=0.9, maxval=1.1)
    pay_m = jax.random.uniform(k[4], minval=0.0, maxval=payload_max)
    body_mass = body_mass.at[pay].set(pay_m)
    body_inertia = model.body_inertia.at[pay].multiply(pay_m / pay_m0)
    body_ipos = model.body_ipos.at[pay].add(jax.random.uniform(k[5], (3,), minval=-com_shift, maxval=com_shift))
    qpos0 = model.qpos0.at[7:].add(jax.random.uniform(k[6], (12,), minval=-0.05, maxval=0.05))
    kp = jax.random.uniform(k[7], (model.nu,), minval=0.8, maxval=1.2) * model.actuator_gainprm[:, 0]
    gainprm = model.actuator_gainprm.at[:, 0].set(kp)
    biasprm = model.actuator_biasprm.at[:, 1].set(-kp)
    # kd scale U(0.8, 1.2) (official BHL). No effect when kd is a joint damping (biasprm[:, 2] = 0).
    biasprm = biasprm.at[:, 2].multiply(jax.random.uniform(k[8], (model.nu,), minval=0.8, maxval=1.2))
    return friction, frictionloss, armature, body_mass, body_inertia, body_ipos, qpos0, gainprm, biasprm

  keys = ["geom_friction", "dof_frictionloss", "dof_armature", "body_mass", "body_inertia",
          "body_ipos", "qpos0", "actuator_gainprm", "actuator_biasprm"]
  vals = rand(rng)
  in_axes = jax.tree_util.tree_map(lambda x: None, model).tree_replace({k: 0 for k in keys})
  model = model.tree_replace(dict(zip(keys, vals)))
  return model, in_axes


if __name__ == "__main__":
  # Stand check: default pose, zero action, no pushes, no noise; the robot must stay up for 1 s.
  cfg = default_config()
  cfg.push_config.enable = False
  cfg.noise_config.level = 0.0
  env = BHLJoystick(cfg)
  # reset() randomises xy, yaw and joint angles: overwrite with the clean home pose.
  state = jax.jit(env.reset)(jax.random.PRNGKey(0))
  data = state.data.replace(qpos=env._init_q, ctrl=env._default_pose, qvel=jp.zeros_like(state.data.qvel))
  state = state.replace(data=mjx.forward(env.mjx_model, data))
  step = jax.jit(env.step)
  z0 = float(state.data.qpos[2])
  for _ in range(int(1.0 / env.dt)):
    state = step(state, jp.zeros(env.action_size))
  up = float(env.get_gravity(state.data)[-1])
  z1 = float(state.data.qpos[2])
  print(f"base z {z0:.3f} -> {z1:.3f} m, upright cos {up:.3f}, done {float(state.done)}")
  assert up > 0.95 and abs(z1 - z0) < 0.05 and state.done == 0, "robot did not stand for 1 s"
  print("stand check OK")
