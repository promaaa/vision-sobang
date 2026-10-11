"""BHL joystick env with the official BHL policy interface, for deployment with the BHL runtime.

Policy input: the 45 values of the official BHL biped policy (docs/locomotion/README.md, section 2.2):
command (3), gyro (3), projected gravity (3), joint pos - default (12), joint vel (12), last action (12).
Policy output: 12 actions, joint target = default + 0.25 * action, 25 Hz. PD 20 / 2 clipped at 6 Nm.

Changes against bhl_env.BHLJoystick (the earlier runs):
- no gait phase and no linear velocity in the policy input (the critic still sees them);
- PD damping is inside the actuator, so the 6 Nm clip includes it (as the BHL runtime); implicitfast integrator;
- command mix with turn on the spot and slow walking, resampled every 5 s;
- tracking rewards with a second, narrow kernel, so slow walking and turning pay more than standing;
- feet air time is rewarded for any non-zero command (BHL gives it only for |v| > 0.1 m/s).
"""

import jax
import jax.numpy as jp
import mujoco

import bhl_env

ACTION_SCALE = 0.25  # official BHL value; the env uses it only through the config
# Official uniform observation noise (BHL biped/env_cfg.py:55-72).
OBS_NOISE = jp.concatenate([jp.zeros(3), jp.full(3, 0.3), jp.full(3, 0.05), jp.full(12, 0.05),
                            jp.full(12, 2.0), jp.zeros(12)])


def default_config():
  c = bhl_env.default_config()
  c.action_scale = ACTION_SCALE
  c.effort_limit = 6.0
  c.payload_max = 3.5
  c.payload_com_shift = 0.05
  c.knee_limit = 1.4
  s = c.reward_config.scales
  s.feet_phase = 0.0  # the policy has no phase input
  s.tracking_lin_vel = 1.5
  s.tracking_ang_vel = 1.0
  c.command_resample_steps = 125  # 5 s
  s.single_stance = 0.0  # set > 0 to use the dense stepping reward below (train.py --single_stance=W)
  return c


class BHLOfficial(bhl_env.BHLJoystick):

  def __init__(self, config=None, config_overrides=None):
    super().__init__(config or default_config(), config_overrides)

  def update_mjx_model(self):
    m = self._mj_model
    if m.opt.integrator != mujoco.mjtIntegrator.mjINT_IMPLICITFAST:
      # BHL PD: tau = clip(kp (q* - q) - kd qd, +-limit). Move kd from the joint into the actuator.
      m.opt.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
      m.actuator_biasprm[:, 2] = -m.dof_damping[6:]
      m.dof_damping[6:] = 0.0
    super().update_mjx_model()

  def _post_init(self):
    super()._post_init()
    self._pay_id = self._mj_model.body("payload").id

  def _get_obs(self, data, info, contact):
    gravity = data.site_xmat[self._site_id].T @ jp.array([0.0, 0.0, -1.0])
    state = jp.hstack([
        info["command"], self.get_gyro(data), gravity,
        data.qpos[7:] - self._default_pose, data.qvel[6:], info["last_act"],
    ])
    info["rng"], key = jax.random.split(info["rng"])
    noise = (2 * jax.random.uniform(key, (45,)) - 1) * OBS_NOISE * self._config.noise_config.level
    privileged = jp.hstack([
        state, self.get_local_linvel(data), self.get_global_angvel(data), data.qpos[2:3],
        data.actuator_force, contact, data.sensordata[self._foot_linvel_sensor_adr].ravel(),
        info["feet_air_time"], self.mjx_model.body_mass[self._pay_id], self.mjx_model.body_ipos[self._pay_id],
    ])
    return {"state": state + noise, "privileged_state": privileged}

  def step(self, state, action):
    state = super().step(state, action)
    state.info["rng"], key = jax.random.split(state.info["rng"])
    new = (state.info["step"] % self._config.command_resample_steps == 0) & (state.info["step"] > 0)
    state.info["command"] = jp.where(new, self.sample_command(key), state.info["command"])
    return state

  def sample_command(self, rng):
    k = jax.random.split(rng, 8)
    u = lambda key, lo, hi: jax.random.uniform(key, minval=lo, maxval=hi)
    general = jp.array([u(k[0], -0.5, 0.5), u(k[1], -0.25, 0.25), u(k[2], -1.0, 1.0)])
    turn = jp.array([0.0, 0.0, u(k[3], 0.2, 0.8) * jp.sign(u(k[4], -1.0, 1.0))])  # turn on the spot
    slow = jp.array([u(k[5], 0.1, 0.3), 0.0, u(k[6], -0.6, 0.6)])  # slow forward walk, with or without turn
    mode = jax.random.choice(k[7], 4, p=jp.array([0.1, 0.25, 0.3, 0.35]))  # stand, turn, slow, general
    return jp.stack([jp.zeros(3), turn, slow, general])[mode]

  # Two kernels: the wide one gives a gradient from the start, the narrow one pays for small speeds.
  def _reward_tracking_lin_vel(self, commands, local_vel):
    e = jp.sum(jp.square(commands[:2] - local_vel[:2]))
    return 0.5 * jp.exp(-e / 0.1) + 0.5 * jp.exp(-e / 0.01)

  def _reward_tracking_ang_vel(self, commands, ang_vel):
    e = jp.square(commands[2] - ang_vel[2])
    return 0.5 * jp.exp(-e / 0.25) + 0.5 * jp.exp(-e / 0.04)

  def _get_reward(self, data, action, info, metrics, done, first_contact, contact):
    rewards = super()._get_reward(data, action, info, metrics, done, first_contact, contact)
    # Like Isaac Lab feet_air_time_positive_biped (used by BHL): while one foot is in the air,
    # pay its air time up to 0.4 s, at every step, for any non-zero command. No gait clock needed.
    single = jp.sum(contact) == 1
    rewards["single_stance"] = (single * jp.minimum(jp.max(info["feet_air_time"]), 0.4)
                                * (jp.linalg.norm(info["command"]) > 0.05))
    return rewards

  def _reward_feet_air_time(self, air_time, first_contact, commands, threshold_min=0.2, threshold_max=0.5):
    air = jp.clip((air_time - threshold_min) * first_contact, max=threshold_max - threshold_min)
    return jp.sum(air) * (jp.linalg.norm(commands) > 0.05)
