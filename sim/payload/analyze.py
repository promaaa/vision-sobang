"""Static torques, CoM offsets, PD standing and push tests for every model variant.

    uv run python analyze.py          # writes results/results.md, results/results.json, results/*.png
    uv run python analyze.py check    # self-check only (fast)
"""
import json
import os
import sys

import mujoco
import numpy as np

import models
from poses import CROUCH, leg_q, place, sole, sole_half

OUT = os.path.join(models.HERE, "results")
LIMITS = (6.0, 20.0)  # Nm: Isaac Lab policy effort limit, MJCF actuator forcerange
LEG = [f"leg_{s}_{j}_joint" for s in ("left", "right")
       for j in ("hip_roll", "hip_yaw", "hip_pitch", "knee_pitch", "ankle_pitch", "ankle_roll")]
# (row label, model variant, hose drag in N)
ROWS = [("biped (no payload)", "biped", 0), ("A water gun", "A_v0", 0), ("B backpack, full", "B", 0),
        ("B backpack, empty", "B_empty", 0), ("full robot with arms (no payload)", "full", 0),
        ("C arms + backpack, full", "C", 0), ("C arms + backpack, empty", "C_empty", 0),
        ("D shell, full", "D", 0), ("D shell, empty", "D_empty", 0), ("E tether, 5 N drag", "E", 5),
        ("E tether, 20 N drag", "E", 20)]


def drag_force(m, d, drag, qfrc):
    """Add the hose drag (backward, horizontal, at the hose connector) to the generalized force qfrc."""
    if drag:
        mujoco.mj_applyFT(m, d, np.array([-drag, 0.0, 0.0]), np.zeros(3), d.site("hose_connector").xpos,
                          m.body("base").id, qfrc)


# ---------- statics ----------
def statics(m, qpos, feet, drag=0.0):
    """Joint torques that hold qpos with zero velocity, the given feet in contact (6D wrench at each sole
    centre). With two feet the split is not unique: take the split with the smallest sum of squared torques."""
    d = mujoco.MjData(m)
    d.qpos[:] = qpos
    mujoco.mj_forward(m, d)
    rhs = d.qfrc_bias.copy()  # gravity (velocity is zero)
    drag_force(m, d, -drag, rhs)  # tau = bias - J^T f - external  ->  subtract external now
    J = []
    for s in feet:
        jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        mujoco.mj_jac(m, d, jp, jr, sole(m, d, s), m.body(f"leg_{s}_ankle_roll").id)
        J += [jp, jr]
    J = np.vstack(J)  # (6 * feet) x nv
    A, b = J[:, :6].T, rhs[:6]  # base rows: contact wrenches carry the whole robot
    f = np.linalg.lstsq(A, b, rcond=None)[0]
    if len(feet) == 2:
        N = np.linalg.svd(A)[2][6:].T  # null space of A: load shift and internal forces between the feet
        r = rhs[6:] - J[:, 6:].T @ f
        f = f + N @ np.linalg.lstsq(J[:, 6:].T @ N, r, rcond=None)[0]
    assert np.allclose(A @ f, b, atol=1e-6)
    tau = rhs[6:] - J[:, 6:].T @ f
    names = [m.joint(m.dof_jntid[i]).name for i in range(6, m.nv)]
    cop_ok = True
    for k, s in enumerate(feet):
        F, M = f[6 * k:6 * k + 3], f[6 * k + 3:6 * k + 6]
        hx, hy = sole_half(m, s)
        cop_ok &= F[2] > 0 and abs(-M[1] / F[2]) <= hx and abs(M[0] / F[2]) <= hy
    return dict(zip(names, tau)), bool(cop_ok), d


def com_and_support(m, d, feet=("left", "right")):
    """Whole-body CoM, support centre (mean of the sole centres) and the sole x range, world frame."""
    c = d.subtree_com[1].copy()
    p = np.array([sole(m, d, s) for s in feet])
    hx = sole_half(m, feet[0])[0]
    return c, p.mean(0), (p[:, 0].min() - hx, p[:, 0].max() + hx)


def single_leg(m, side, drag=0.0):
    """Sway the pelvis over the stance foot (bisection on the sway angle) and hold all weight on it."""
    sign = -1 if side == "left" else 1
    lim = min(m.joint("leg_left_hip_roll_joint").range[1], -m.joint("leg_left_hip_roll_joint").range[0])
    lo, hi = 0.0, lim
    for _ in range(30):
        a = (lo + hi) / 2
        q = place(m, leg_q(models.STAND, sign * a), stance=side)
        d = mujoco.MjData(m)
        d.qpos[:] = q
        mujoco.mj_kinematics(m, d)
        mujoco.mj_comPos(m, d)
        gap = (d.subtree_com[1][1] - sole(m, d, side)[1]) * sign  # > 0: CoM still on the inner side
        lo, hi = (a, hi) if gap > 0 else (lo, a)
    tau, ok, d = statics(m, q, [side], drag)
    return tau, ok, a, d


def static_report(variant, drag):
    m = models.load(variant) if isinstance(variant, str) else variant
    out = {"mass": float(m.body_subtreemass[1])}
    q = place(m, leg_q(models.STAND))
    tau, ok, d = statics(m, q, ["left", "right"], drag)
    c, centre, (x0, x1) = com_and_support(m, d)
    out.update(com=c.tolist(), com_dx=float(c[0] - centre[0]), com_dy=float(c[1] - centre[1]),
               support_x=[float(x0 - centre[0]), float(x1 - centre[0])], com_h=float(c[2]))
    out["stand"] = {"tau": tau, "cop_ok": ok}
    tau, ok, d = statics(m, place(m, leg_q(CROUCH)), ["left", "right"], drag)
    out["crouch"] = {"tau": tau, "cop_ok": ok, "com_dx": float(com_and_support(m, d)[0][0] - com_and_support(m, d)[1][0])}
    for side in ("left", "right"):
        tau, ok, a, d = single_leg(m, side, drag)
        out[f"single_{side}"] = {"tau": tau, "cop_ok": ok, "sway": a}
    for k in ("stand", "crouch", "single_left", "single_right"):
        t = out[k]["tau"]
        j = max(LEG, key=lambda n: abs(t[n]))
        out[k].update(peak=abs(t[j]), peak_joint=j)
    out["single"] = max((out["single_left"], out["single_right"]), key=lambda r: r["peak"])
    arms = [n for n in out["stand"]["tau"] if n.startswith("arm")]
    if arms:
        out["arm_peak"] = max(abs(out["stand"]["tau"][n]) for n in arms)
    return out


# ---------- dynamics ----------
def simulate(m, kp, kd, tau_max, t_end=10.0, push=0.0, drag=0.0):
    """PD control to the 'stand' keyframe with torque clipping. push: impulse (N s, + forward) on the base
    over 0.1 s starting at t = 1 s. Returns (stood, height drop m, X): X = peak |leg torque| in the last 2 s
    if the robot stood, else the time of the fall."""
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0)
    jnt = m.actuator_trnid[:, 0]
    qa, va = m.jnt_qposadr[jnt], m.jnt_dofadr[jnt]
    target, z0 = d.qpos[qa].copy(), d.qpos[2]
    leg = np.array([m.joint(j).name in LEG for j in jnt])
    base = m.body("base").id
    peak, dt = 0.0, m.opt.timestep
    while d.time < t_end:
        tau = np.clip(kp * (target - d.qpos[qa]) - kd * d.qvel[va], -tau_max, tau_max)
        d.ctrl[:] = tau
        d.qfrc_applied[:] = 0
        drag_force(m, d, drag, d.qfrc_applied)
        d.xfrc_applied[base, 0] = push / 0.1 if 1.0 <= d.time < 1.1 else 0.0
        mujoco.mj_step(m, d)
        if d.time > t_end - 2:
            peak = max(peak, np.abs(tau[leg]).max())
        tilt = np.arccos(np.clip(d.xmat[base][8], -1, 1))
        if z0 - d.qpos[2] > 0.15 or tilt > 0.6:
            return False, float(z0 - d.qpos[2]), float(d.time)
    return True, float(z0 - d.qpos[2]), peak


def max_push(m, kp, kd, tau_max, sign, drag=0.0, hi=20.0, iters=7):
    """Largest impulse (N s) the PD stance survives (no fall within 3 s after the push), by bisection."""
    if not simulate(m, kp, kd, tau_max, 4.0, 0.0, drag)[0]:
        return 0.0
    lo = 0.0
    for _ in range(iters):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if simulate(m, kp, kd, tau_max, 4.0, sign * mid, drag)[0] else (lo, mid)
    return lo


# (kp, kd, torque limit). kp 20 / kd 2 = Isaac Lab policy gains. kp 200 / kd 5 is an extra, stiffer setting:
# with plain joint PD (no balance feedback) the heavier models only stand when the joints are this stiff.
CONTROLLERS = [(20, 2, 6), (20, 2, 20), (50, 2, 6), (50, 2, 20), (200, 5, 6), (200, 5, 20)]
PUSH_CONTROLLERS = [(50, 2, 20), (200, 5, 6), (200, 5, 20)]


def dynamic_report(variant, drag):
    m = models.load(variant) if isinstance(variant, str) else variant
    out = {}
    for kp, kd, lim in CONTROLLERS:
        stood, drop, peak = simulate(m, kp, kd, lim, 10.0, 0.0, drag)
        out[f"kp{kp}_lim{lim}"] = {"stood": stood, "drop": drop, "peak_or_fall_time": peak}
    for kp, kd, lim in PUSH_CONTROLLERS:
        out[f"push_kp{kp}_lim{lim}"] = {"fwd": max_push(m, kp, kd, lim, 1, drag), "back": max_push(m, kp, kd, lim, -1, drag)}
    return out


# ---------- check ----------
def self_check():
    models.self_check()
    for v in ("biped",):  # the full robot holds the asymmetric ARM_POSE, so only the biped is symmetric
        r = static_report(v, 0)
        t = r["stand"]["tau"]
        for j in LEG:  # symmetric pose, symmetric robot: left and right torques equal in size
            o = j.replace("left", "right") if "left" in j else j.replace("right", "left")
            assert abs(abs(t[j]) - abs(t[o])) < 0.05, (v, j, t[j], t[o])
        # the feet carry the whole weight: total vertical contact force = m g (checked inside statics via A f = b)
        assert r["stand"]["cop_ok"] and abs(r["com_dy"]) < 0.005, (v, r["com_dy"])
    print("self-check statics: left/right torques symmetric in the stand pose, CoP inside the feet")


if __name__ == "__main__":
    self_check()
    if sys.argv[1:] == ["check"]:
        sys.exit()
    os.makedirs(OUT, exist_ok=True)
    res = {}
    for label, v, drag in ROWS:
        res[label] = {"variant": v, "drag": drag, **static_report(v, drag)}
        print(f"{label:34s} {res[label]['mass']:5.2f} kg  stand {res[label]['stand']['peak']:5.2f}  "
              f"crouch {res[label]['crouch']['peak']:5.2f}  single {res[label]['single']['peak']:5.2f} Nm", flush=True)
    json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    for label, v, drag in ROWS:
        res[label]["dyn"] = dynamic_report(v, drag)
        print(label, res[label]["dyn"], flush=True)
        json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
