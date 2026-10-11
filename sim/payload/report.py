"""Tables (results/results.md) and plots (results/*.png) from results/results.json and results/placement.json.

    uv run python report.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import analyze  # noqa: E402
import models  # noqa: E402

OUT = analyze.OUT
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"  # categorical slots 1-3
PITCH = ("hip_pitch", "knee_pitch", "ankle_pitch")
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": INK2,
                     "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def pk(t, pitch_only=False):
    js = [j for j in analyze.LEG if not pitch_only or any(p in j for p in PITCH)]
    j = max(js, key=lambda n: abs(t[n]))
    return abs(t[j]), j.replace("leg_", "").replace("_joint", "")


def limit_lines(ax):
    for v in analyze.LIMITS:
        ax.axvline(v, color=INK, lw=1.2, ls="--", zorder=4)
        ax.text(v - 0.2, ax.get_ylim()[1] - 0.3, f"{v:g} Nm limit", ha="right", va="top", color=INK, fontsize=9)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    res = json.load(open(os.path.join(OUT, "results.json")))
    labels = list(res)
    lines = []

    # ---- table 1: statics ----
    lines += ["| Model | Total mass (kg) | CoM height (m) | CoM fore-aft offset (mm, + = forward) | Stand peak (Nm, joint) "
              "| Crouch peak (Nm, joint) | Single-leg peak, all joints (Nm, joint) | Single-leg peak, pitch joints (Nm, joint) "
              "| Margin to 6 Nm, single-leg pitch (Nm) | Margin to 20 Nm, single-leg all (Nm) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for k in labels:
        r = res[k]
        st, cr, sg, sp = pk(r["stand"]["tau"]), pk(r["crouch"]["tau"]), pk(r["single"]["tau"]), pk(r["single"]["tau"], True)
        lines.append(f"| {k} | {r['mass']:.2f} | {r['com_h']:.3f} | {1000 * r['com_dx']:+.0f} | {st[0]:.1f} ({st[1]}) "
                     f"| {cr[0]:.1f} ({cr[1]}) | {sg[0]:.1f} ({sg[1]}) | {sp[0]:.1f} ({sp[1]}) | {6 - sp[0]:+.1f} "
                     f"| {20 - sg[0]:+.1f} |")
    cop = [k for k in labels if not all(res[k][p]["cop_ok"] for p in ("stand", "crouch", "single_left", "single_right"))]
    lines += ["", f"Centre of pressure outside a foot (pose not statically possible): {', '.join(cop) or 'none'}.", ""]
    lines += ["Peak arm joint torque in the stand pose, arms in ARM_POSE:", ""]
    lines += [f"- {k}: {res[k]['arm_peak']:.1f} Nm" for k in labels if "arm_peak" in res[k]] + [""]

    # ---- table 2: dynamics ----
    ctl = [f"kp{kp}_lim{lim}" for kp, kd, lim in analyze.CONTROLLERS]
    head = [f"kp {kp} / kd {kd} / {lim} Nm" for kp, kd, lim in analyze.CONTROLLERS]
    lines += ["| Model | " + " | ".join(head) + " | Push fwd / back (N s), kp 50 / kd 2 / 20 Nm "
              "| Push fwd / back (N s), kp 200 / kd 5 / 6 Nm | Push fwd / back (N s), kp 200 / kd 5 / 20 Nm |",
              "|---" * (len(head) + 4) + "|"]
    for k in labels:
        dy = res[k]["dyn"]
        cells = []
        for c in ctl:
            s = dy[c]
            cells.append(f"stands, {s['peak_or_fall_time']:.1f} Nm" if s["stood"] else f"falls at {s['peak_or_fall_time']:.1f} s")
        pushes = [f"{dy[p]['fwd']:.1f} / {dy[p]['back']:.1f}" for p in ("push_kp50_lim20", "push_kp200_lim6", "push_kp200_lim20")]
        lines.append(f"| {k} | " + " | ".join(cells + pushes) + " |")
    lines += ["", "\"stands, X Nm\": the robot stays up for 10 s. X is the peak leg torque in the last 2 s. "
              "Push values: the largest impulse on the torso (0.1 s) with no fall in the next 3 s. 0 means that the "
              "model does not stand.", ""]

    # ---- plot 1: peak torque per model and pose ----
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(8, 6.2))
    for i, (key, name, c) in enumerate([("stand", "Stand, both feet", S1), ("crouch", "Crouch, knee 1.0 rad", S2),
                                        ("single", "Single-leg stance", S3)]):
        ax.barh(y + (1 - i) * 0.27, [pk(res[k][key]["tau"])[0] for k in labels], height=0.25, color=c, label=name,
                zorder=2)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 22)
    ax.set_ylim(-1, len(labels))
    limit_lines(ax)
    ax.set_xlabel("Peak static leg joint torque (Nm)")
    ax.set_title("Static peak leg torque vs. the 6 Nm policy limit and the 20 Nm motor limit", loc="left", fontsize=11)
    ax.legend(frameon=False, loc="center left", bbox_to_anchor=(0.62, 0.5))
    ax.grid(axis="x", color=GRID, zorder=0)
    save(fig, "peak_torque.png")

    # ---- plot 2: CoM fore-aft offset ----
    fig, ax = plt.subplots(figsize=(8, 5.2))
    sx = res[labels[0]]["support_x"]
    ax.axvspan(1000 * sx[0], 1000 * sx[1], color=GRID, zorder=0)
    ax.text(1000 * sx[1] - 3, len(labels) - 0.6, "feet (heel to toe)", ha="right", va="center", color=INK2, fontsize=9)
    dx = [1000 * res[k]["com_dx"] for k in labels]
    ax.hlines(y, 0, dx, color=S1, lw=2, zorder=2)
    ax.plot(dx, y, "o", color=S1, ms=8, zorder=3)
    for yi, v in zip(y, dx):
        ax.text(v + (4 if v >= 0 else -4), yi, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", color=INK, fontsize=9)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y, labels)
    ax.set_ylim(-0.8, len(labels))
    ax.set_xlabel("CoM offset from the centre of the feet, stand pose (mm, + = forward)")
    ax.set_title("Whole-body CoM fore-aft position over the feet", loc="left", fontsize=11)
    save(fig, "com_offset.png")

    # ---- plot 3: push survival ----
    fig, ax = plt.subplots(figsize=(8, 5.6))
    p = "push_kp200_lim20"
    ax.barh(y + 0.17, [res[k]["dyn"][p]["fwd"] for k in labels], height=0.32, color=S1, label="Push forward", zorder=2)
    ax.barh(y - 0.17, [res[k]["dyn"][p]["back"] for k in labels], height=0.32, color=S2, label="Push backward", zorder=2)
    for yi, k in zip(y, labels):
        if res[k]["dyn"][p]["fwd"] == res[k]["dyn"][p]["back"] == 0:
            ax.text(0.1, yi, "falls with no push", va="center", color=INK2, fontsize=9)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Largest torso impulse survived without stepping (N s)")
    ax.set_title("Push test, joint PD kp 200 / kd 5, 20 Nm limit", loc="left", fontsize=11)
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", color=GRID, zorder=0)
    save(fig, "push.png")

    # ---- plot 4: placement maps ----
    pl = os.path.join(OUT, "placement.json")
    if os.path.exists(pl):
        P = json.load(open(pl))
        xs, zs = sorted({g["x"] for g in P["grid"]}), sorted({g["z"] for g in P["grid"]})
        grid = {(g["x"], g["z"]): g for g in P["grid"]}
        fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
        for ax, (key, title, cmap) in zip(axs, [
                ("single_pitch", f"Single-leg peak pitch torque (Nm), +{P['probe']:g} kg", "Blues"),
                ("push_min", f"Smallest push survived, fwd or back (N s), +{P['probe']:g} kg", "Blues")]):
            val = np.array([[min(grid[x, z]["push_fwd"], grid[x, z]["push_back"]) if key == "push_min"
                             else grid[x, z][key] for x in xs] for z in zs])
            im = ax.imshow(val, origin="lower", cmap=cmap, aspect="auto",
                           extent=[xs[0] - 0.025, xs[-1] + 0.025, zs[0] - 0.05, zs[-1] + 0.05])
            for i, z in enumerate(zs):
                for j, x in enumerate(xs):
                    v = val[i, j]
                    ax.text(x, z, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                            color="white" if v > val.min() + 0.6 * (val.max() - val.min()) else INK)
            ax.axhline(models.T, color=INK2, lw=1, ls=":")
            ax.set_title(title, loc="left", fontsize=10)
            ax.set_xlabel("Payload x, robot frame (m, + = forward)")
            fig.colorbar(im, ax=ax, shrink=0.8)
        axs[0].set_ylabel("Payload height z above the floor (m)")
        axs[0].text(xs[0] - 0.02, models.T + 0.01, "torso top", color=INK2, fontsize=8, va="bottom")
        fig.suptitle("Where to put payload: a 2 kg point mass moved over a grid on the biped", x=0.01, ha="left")
        save(fig, "placement.png")

        for where, b in P["budget"].items():
            lines += [f"Mass budget: extra point mass at the {where}, robot frame, on the biped:", "",
                      "| Added mass (kg) | Stand peak (Nm) | Crouch peak (Nm) | Single-leg peak, pitch joints (Nm) "
                      "| Single-leg peak, all joints (Nm) |", "|---|---|---|---|---|"]
            lines += [f"| {r['mass']:.0f} | {r['stand']:.1f} | {r['crouch']:.1f} | {r['single_pitch']:.1f} | {r['single']:.1f} |"
                      for r in b if r["mass"] % 2 == 0]
            lines.append("")
            for key, name in [("stand", "stand"), ("crouch", "crouch"), ("single_pitch", "single-leg, pitch joints"),
                              ("single", "single-leg, all joints")]:
                for lim in analyze.LIMITS:
                    over = [r["mass"] for r in b if r[key] > lim]
                    lines.append(f"- {name}: " + (f"above {lim:g} Nm already with 0 kg added" if over and over[0] == 0
                                 else f"above {lim:g} Nm from {over[0]:.1f} kg added" if over
                                 else f"at or below {lim:g} Nm up to 10 kg added"))
            lines.append("")
    open(os.path.join(OUT, "results.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
