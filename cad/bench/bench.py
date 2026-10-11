"""Table-top bench rig for the STS3215 pan-tilt module, the cameras, the water system and the electronics.

    cad/parts/.venv/bin/python cad/bench/bench.py

Bench frame = module frame of cad/parts: x forward, y left, z up, mm, origin on the top face of the two 2020
rails, at their centre. The table top is at z = -H_BASE. Imports the module (cad/parts/top_module_sts3215.py)
and the bottle cradle (cad/backpack/body.py). Writes cad/bench/out/ and runs the checks.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from build123d import Align, CenterOf, Cylinder, Pos, RegularPolygon, Rot, export_step, export_stl, extrude

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE.parent / "parts"), str(HERE.parent / "backpack")]
import body as bp                     # noqa: E402  cad/backpack: bottle cradle, bottle and pump sizes
import top_module as tm               # noqa: E402  cad/parts: helpers, mass estimate, wall scan
import top_module_sts3215 as ts       # noqa: E402  cad/parts: STS3215 module
from top_module import box, cyl, slot  # noqa: E402

OUT = HERE / "out"

# ---------------- parameters ----------------
RAIL_X, RAIL_LEN = tm.RAIL_X, 140.0     # two 2020 rails along y at x = +-60 (torso spacing), cut length 140 mm
RAIL_KG_M = 0.5                         # 2020 profile mass per metre, GUESS (typical catalogue value)
H_BASE = 80.0                           # table top to the rail top. Keeps the pump under the gun at 30 deg nose-up.
BASE_X, BASE_Y, BASE_T = 170.0, 180.0, 5.0
SADDLE_W, SADDLE_WALL = 20.0, 3.0       # hollow block under each rail, as wide as the rail (the pan servo hangs 1.9 mm inside)
RAIL_SCREW_Y = 40.0                     # M5 from below into T-nuts in the bottom slot (deck uses y = +-55 on top)
CLAMP_TAB = (50.0, 18.0, 14.0)          # clamp tab length (x), depth (y), open slot width
TRIPOD_XY = (-30.0, 32.0)               # tripod screw: near the CoM, beside the hanging pan servo
NUT14_AF, NUT14_T = 11.11, 5.56         # 1/4"-20 hex nut: 7/16 in across flats, 7/32 in thick

TRAY_GAP = 40.0                         # the tray stands free, this far behind the base (outside the gun sweep)
TRAY_X1 = -BASE_X / 2 - TRAY_GAP
TRAY_X0, TRAY_Y, TRAY_T = TRAY_X1 - 200.0, 100.0, 3.0   # tray 200 x 200, floor thickness
RIM_H, RIM_T = 12.0, 2.5                # drip rim keeps leaks in the tray
PUMP_XC, PUMP_YC = TRAY_X1 - 50.0, -12.0        # pump centre on the tray: lying on its feet, motor along y
PUMP_BOSS = 8.0                         # M4 insert (8.5 mm) needs the boss + floor
BOTTLE_XY = (TRAY_X0 + 56.5, 40.0)      # bottle centre: cradle backing against the rear post (checked: outside the gun sweep)

BOX_IN = (160.0, 100.0, 90.0)           # electronics box inside size x, y, z (90: room for the e-stop depth)
BOX_WALL, BOX_FLOOR = 2.5, 3.0
BOX_AT = (-225.0, -235.0)               # box centre on the table, beside the tray, outside the gun sweep (checked)
ESTOP_D = 22.3                          # 22 mm e-stop panel cutout (Koino KSEP2240-22S drawing)
ESTOP_XY = (32.0, 24.0)                 # e-stop over the relay module, from the box centre
GLAND_D = 12.5                          # PG7 cable gland: thread and panel hole 12.5 mm (Alpha Wire PPS7)

GUN_REAR, GUN_W = 145.0 - tm.GUN_COM_DX, tm.GUN_W   # stand-in of cad/concepts.py: rear block ends 145 mm behind the body centre
TILT_UP = 30.0                          # deg nose-up for the bench (jet speed test at 30 deg)
PAN_RANGE = 180.0                       # deg each side for the stability check (all pan angles)
WATER_KG, BOTTLE_KG, PUMP_KG = 1.0, 0.18, 0.57   # full 1 L bottle; bottle mass GUESS; pump from the Seaflo brochure

Z_TABLE = -H_BASE
TRAY_Z0 = Z_TABLE + TRAY_T              # tray floor top


# ---------------- parts ----------------
def base(tripod=False):
    """Bottom plate, two hollow saddles that carry the rails, locating lips, clamp tabs or a tripod nut."""
    x0, x1, y0, y1 = -BASE_X / 2, BASE_X / 2, -BASE_Y / 2, BASE_Y / 2
    zt = -20.0                                          # rail bottom
    b = box(x0, x1, y0, y1, Z_TABLE, Z_TABLE + BASE_T)
    for sx in (-1, 1):
        xc = sx * RAIL_X
        sad = box(xc - SADDLE_W / 2, xc + SADDLE_W / 2, -RAIL_LEN / 2, RAIL_LEN / 2, Z_TABLE, zt)
        sad -= box(xc - SADDLE_W / 2 + SADDLE_WALL, xc + SADDLE_W / 2 - SADDLE_WALL, -RAIL_LEN / 2 + SADDLE_WALL,
                   RAIL_LEN / 2 - SADDLE_WALL, Z_TABLE + BASE_T, zt - SADDLE_WALL)
        for y in (-RAIL_SCREW_Y, 0.0, RAIL_SCREW_Y):    # inner ribs
            sad += box(xc - SADDLE_W / 2, xc + SADDLE_W / 2, y - 1.5, y + 1.5, Z_TABLE, zt)
        b += sad
        xl = xc + sx * (10 + 1.25)                      # outer lip only: the pan servo hangs 1.9 mm inside the rear rail
        b += box(xl - 1.25, xl + 1.25, -RAIL_LEN / 2, RAIL_LEN / 2, zt, zt + 6)
        for y in (-RAIL_SCREW_Y - 8, RAIL_SCREW_Y + 8):  # M5 x 25 from below: head 20 mm under the rail, in a column
            b += cyl(SADDLE_W - 2 * SADDLE_WALL, Z_TABLE, zt, xc, y)
            b -= cyl(tm.M5_CLR, Z_TABLE - 1, zt + 1, xc, y)
            b -= cyl(10.0, Z_TABLE - 1, zt - 20, xc, y)
    for x in (-50.0, 0.0, 50.0):                        # cross ribs between the saddles
        b += box(-RAIL_X + SADDLE_W / 2, RAIL_X - SADDLE_W / 2, x * 1.6 - 1.5, x * 1.6 + 1.5, Z_TABLE, Z_TABLE + 15)
    if tripod:   # boss inside the base, beside the hanging pan servo; nut drops in from the top
        zb = Z_TABLE + BASE_T + 12
        b += cyl(30.0, Z_TABLE, zb, TRIPOD_XY[0], TRIPOD_XY[1])
        b -= cyl(6.6, Z_TABLE - 1, zb + 1, TRIPOD_XY[0], TRIPOD_XY[1])                    # 1/4"-20 screw clearance
        b -= Pos(TRIPOD_XY[0], TRIPOD_XY[1], zb - NUT14_T - 0.5) * extrude(RegularPolygon(NUT14_AF / 2 + 0.15, 6, major_radius=False), NUT14_T + 1)
    else:
        L, D, W = CLAMP_TAB
        for sx in (-1, 1):
            for sy in (-1, 1):
                xc, yo = sx * (BASE_X / 2 - L / 2), sy * BASE_Y / 2
                tab = box(xc - L / 2, xc + L / 2, min(yo, yo + sy * D), max(yo, yo + sy * D), Z_TABLE, Z_TABLE + BASE_T)
                tab -= box(xc - W / 2, xc + W / 2, min(yo + sy * 6, yo + sy * (D + 1)), max(yo + sy * 6, yo + sy * (D + 1)), Z_TABLE - 1, Z_TABLE + BASE_T + 1)
                b += tab
    return b


def cradle_pose(shape):
    """Backpack cradle frame -> bench: bottle at BOTTLE_XY, turned 180 deg so the backing is behind the bottle."""
    return Pos(BOTTLE_XY[0], BOTTLE_XY[1], TRAY_Z0) * (Rot(Z=180) * (Pos(-bp.TANK_X, -bp.TANK_Y, -bp.CR_FLOOR_Z) * shape))


def tray():
    """Floor with a drip rim, pump bosses (M4 inserts), and a rear post that takes the backpack cradle."""
    t = box(TRAY_X0, TRAY_X1, -TRAY_Y, TRAY_Y, Z_TABLE, TRAY_Z0)
    t += box(TRAY_X0, TRAY_X1, -TRAY_Y, TRAY_Y, Z_TABLE, TRAY_Z0 + RIM_H) - box(
        TRAY_X0 + RIM_T, TRAY_X1 - RIM_T, -TRAY_Y + RIM_T, TRAY_Y - RIM_T, TRAY_Z0, TRAY_Z0 + RIM_H + 1)
    t -= cyl(8.0, Z_TABLE - 1, TRAY_Z0 + 1, TRAY_X0 + 15, -TRAY_Y + 15)        # drain hole (plug or tube)
    hx, hy = bp.PUMP_HOLES[1] / 2, bp.PUMP_HOLES[0] / 2                     # 55 along the motor (y), 79 across (x)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = PUMP_XC + sx * hy, PUMP_YC + sy * hx
            t += cyl(bp.BOSS_D, TRAY_Z0, TRAY_Z0 + PUMP_BOSS, x, y)
            t -= cyl(bp.INSERT_D, TRAY_Z0 + PUMP_BOSS - bp.INSERT_L, TRAY_Z0 + PUMP_BOSS + 1, x, y)
    # rear post for the cradle: the cradle backing bolts to it with 4 M4 screws and nuts
    xb = BOTTLE_XY[0] - (bp.XP1 - bp.TANK_X)                                # backing rear face
    yc = BOTTLE_XY[1]
    post = box(xb - 5, xb, yc - 45, yc + 45, TRAY_Z0, TRAY_Z0 + 125)
    for dy in (-bp.BOLT_DY, bp.BOLT_DY):
        for z in (bp.INS_LO_Z, bp.CR_NUT_Z):
            zz = z - bp.CR_FLOOR_Z + TRAY_Z0
            post -= Pos(xb - 6, yc + dy, zz) * (Rot(Y=90) * Cylinder(tm.M4_CLR / 2, 8, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    t += post
    return t


def ebox():
    """Electronics box: floor bosses, PG7 gland holes, vents high on the short walls (under the lid skirt)."""
    ix, iy, iz = BOX_IN
    w, f = BOX_WALL, BOX_FLOOR
    cx, cy = BOX_AT
    b = box(cx - ix / 2 - w, cx + ix / 2 + w, cy - iy / 2 - w, cy + iy / 2 + w, Z_TABLE, Z_TABLE + f + iz)
    b -= box(cx - ix / 2, cx + ix / 2, cy - iy / 2, cy + iy / 2, Z_TABLE + f, Z_TABLE + f + iz + 1)
    for sx in (-1, 1):                         # lid screw bosses in the corners (M3 self-tapping)
        for sy in (-1, 1):
            x, y = cx + sx * (ix / 2 - 4), cy + sy * (iy / 2 - 4)
            b += cyl(8.0, Z_TABLE + f, Z_TABLE + f + iz, x, y)
            b -= cyl(tm.M3_PILOT, Z_TABLE + f + iz - 12, Z_TABLE + f + iz + 1, x, y)
    for x, y, d in BOX_BOSSES:                 # component stand-offs, 6 mm high
        b += cyl(d + 4.5, Z_TABLE + f, Z_TABLE + f + 6, cx + x, cy + y)
        b -= cyl(d, Z_TABLE + f, Z_TABLE + f + 7, cx + x, cy + y)
    for i in range(4):                         # PG7 glands on the -x wall, low
        y = cy - iy / 2 + 15 + i * (iy - 30) / 3
        b -= Pos(cx - ix / 2 - w - 1, y, Z_TABLE + f + 14) * (Rot(Y=90) * Cylinder(GLAND_D / 2, w + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    for sx in (-1, 1):                         # vents on both short walls, just under the top edge
        for k in range(4):
            y = cy - 30 + k * 20
            b -= box(cx + sx * (ix / 2 + w / 2) - w, cx + sx * (ix / 2 + w / 2) + w, y - 6, y + 6, Z_TABLE + f + iz - 9, Z_TABLE + f + iz - 4)
    return b


def ebox_lid():
    """Lid with a skirt that hangs 10 mm over the walls (covers the vents), e-stop hole, 4 M3 holes."""
    ix, iy, iz = BOX_IN
    w, f = BOX_WALL, BOX_FLOOR
    cx, cy = BOX_AT
    z0 = Z_TABLE + f + iz
    g = 1.0                                    # skirt gap
    l = box(cx - ix / 2 - w - g - 2.5, cx + ix / 2 + w + g + 2.5, cy - iy / 2 - w - g - 2.5, cy + iy / 2 + w + g + 2.5, z0 - 10, z0 + 3)
    l -= box(cx - ix / 2 - w - g, cx + ix / 2 + w + g, cy - iy / 2 - w - g, cy + iy / 2 + w + g, z0 - 11, z0)
    l -= cyl(ESTOP_D, z0 - 1, z0 + 4, cx + ESTOP_XY[0], cy + ESTOP_XY[1])
    for sx in (-1, 1):
        for sy in (-1, 1):
            l -= cyl(tm.M3_CLR, z0 - 1, z0 + 4, cx + sx * (ix / 2 - 4), cy + sy * (iy / 2 - 4))
    return l


# component stand-offs in the box (x, y from the box centre, pilot hole). Positions are a layout proposal.
BOX_BOSSES = (
    [(32 + sx * 23.5, -30 + sy * 5.7, 1.8) for sx in (-1, 1) for sy in (-1, 1)]     # Pico 2: holes 47 x 11.4, d 2.1 (datasheet), M2
    + [(32 + sx * 22.0, 24 + sy * 16.25, 2.5) for sx in (-1, 1) for sy in (-1, 1)]  # relay module 50 x 38, holes 44 x 32.5, d 3, M3
)
# DC-DC converter (HAM5017): no size published. Free area 74 x 74 x 32 mm at (-41, -11), the size of similar
# 120 W converters (GUESS). It sits on foam tape or a strap: no bosses.
DCDC = (-41.0, -11.0, 74.0, 74.0, 32.0)


def rails():
    return [box(sx * RAIL_X - 10, sx * RAIL_X + 10, -RAIL_LEN / 2, RAIL_LEN / 2, -20, 0) for sx in (-1, 1)]


def refs():
    """Bought parts for checks and renders."""
    bottle = cradle_pose(bp.tank_ref())
    pump = box(PUMP_XC - bp.PUMP_W / 2, PUMP_XC + bp.PUMP_W / 2, PUMP_YC - bp.PUMP_L / 2, PUMP_YC + bp.PUMP_L / 2,
               TRAY_Z0 + PUMP_BOSS, TRAY_Z0 + PUMP_BOSS + bp.PUMP_H)
    r = rails()
    return {"ref_rail_r": r[0], "ref_rail_f": r[1], "ref_bottle": bottle, "ref_pump": pump}


PARTS = {
    "base_clamp": base,
    "base_tripod": lambda: base(tripod=True),
    "tray": tray,
    "cradle": lambda: cradle_pose(bp.cradle()),
    "ebox": ebox,
    "ebox_lid": ebox_lid,
}


# ---------------- checks ----------------
def gun_low_z(tilt_up_deg):
    """Lowest point of the gun rear (bench z) at a nose-up tilt; the gun bottom sits on the payload plate."""
    zt = ts.Z_TILT
    zb = ts.Z_U1 + tm.PLATE_T - zt                     # gun bottom above the tilt axis
    rear = GUN_REAR                                    # rear end behind the tilt axis
    a = math.radians(tilt_up_deg)
    return zt + zb * math.cos(a) - rear * math.sin(a), rear


def hull(points):
    pts = sorted(set(points))
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]


def margin(poly, p):
    """Distance from point p to the nearest edge of convex polygon poly (counter-clockwise); < 0 outside."""
    d = []
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        ex, ey = x2 - x1, y2 - y1
        d.append(((p[0] - x1) * ey - (p[1] - y1) * ex) / -math.hypot(ex, ey))
    return min(d)


def stability(shapes, ref):
    """CoM of the free-standing rig (base, rails, tray, cradle, pump, full bottle, STS module with the gun)
    for every pan angle; tipping margin = distance from the CoM to the edge of the base + tray footprint."""
    mod_shapes = {n: f() for n, f in ts.PARTS.items()}
    mod_ref = ts.refs()
    ref_mass = dict(tm.REF_MASS, ref_pan_servo=0.089, ref_tilt_servo=0.089)
    turning = {"pan_yoke", "tilt_u", "payload_plate", "cam_usb32", "cam_mlx90640", "ref_tilt_servo", "ref_gun",
               "ref_cam_usb32", "ref_cam_thermal"}
    fixed, turn = [], []
    for n, s in {**mod_shapes, **mod_ref}.items():
        m = tm.mass(s)[0] / 1000 if n in mod_shapes else ref_mass[n]
        (turn if n in turning else fixed).append((m, s.center(CenterOf.MASS)))
    fixed.append((tm.mass(shapes["base_clamp"])[0] / 1000, shapes["base_clamp"].center(CenterOf.MASS)))
    for n in ("ref_rail_r", "ref_rail_f"):
        fixed.append((RAIL_KG_M * RAIL_LEN / 1000, ref[n].center(CenterOf.MASS)))
    foot = []
    for n in ("base_clamp",):
        bb = shapes[n].bounding_box()
        foot += [(bb.min.X, bb.min.Y), (bb.max.X, bb.min.Y), (bb.max.X, bb.max.Y), (bb.min.X, bb.max.Y)]
    poly = hull(foot)
    mf = sum(m for m, _ in fixed)
    mt = sum(m for m, _ in turn)
    fx = sum(m * v.X for m, v in fixed) / mf, sum(m * v.Y for m, v in fixed) / mf
    tx = sum(m * v.X for m, v in turn) / mt - tm.PAN_X, sum(m * v.Y for m, v in turn) / mt
    worst = None
    for deg in range(-int(PAN_RANGE), int(PAN_RANGE) + 1, 5):
        a = math.radians(deg)
        px = tm.PAN_X + tx[0] * math.cos(a) - tx[1] * math.sin(a)
        py = tx[0] * math.sin(a) + tx[1] * math.cos(a)
        cx, cy = (mf * fx[0] + mt * px) / (mf + mt), (mf * fx[1] + mt * py) / (mf + mt)
        mg = margin(poly, (cx, cy))
        if worst is None or mg < worst[0]:
            worst = (mg, deg, cx, cy)
    a90 = math.radians(90)
    p90 = (tm.PAN_X + tx[0] * math.cos(a90) - tx[1] * math.sin(a90), tx[0] * math.sin(a90) + tx[1] * math.cos(a90))
    c90 = ((mf * fx[0] + mt * p90[0]) / (mf + mt), (mf * fx[1] + mt * p90[1]) / (mf + mt))
    return {"mass_kg": round(mf + mt, 2), "turning_kg": round(mt, 2), "footprint_mm": [[round(x), round(y)] for x, y in poly],
            "com_pan90_mm": [round(c90[0], 1), round(c90[1], 1)], "margin_pan90_mm": round(margin(poly, c90), 1),
            "worst_margin_mm": round(worst[0], 1), "worst_pan_deg": worst[1]}


def check(shapes, ref):
    for n, s in shapes.items():
        bb = s.bounding_box()
        size = sorted([bb.size.X, bb.size.Y, bb.size.Z])
        assert all(a <= b for a, b in zip(size, sorted(tm.BED))), f"{n} does not fit the bed: {size}"
    # the pan servo foot of the module hangs under the deck: it must clear the base plate
    assert Z_TABLE + BASE_T + 2 < ts.Z0 - ts.ST_H - 3, "pan servo foot hits the base plate"
    # gun sweep: at TILT_UP nose-up the gun rear (any pan angle) stays above the pump and the tray
    zlow, rear = gun_low_z(TILT_UP)
    top = TRAY_Z0 + PUMP_BOSS + bp.PUMP_H
    assert zlow > top + 5, f"gun rear {zlow:.0f} mm hits the pump top {top:.0f} mm"
    r_sweep = math.hypot(rear, GUN_W / 2) + 5
    bx, by = BOTTLE_XY
    r_bottle = math.hypot(bx - tm.PAN_X, by) - bp.TANK_R
    assert r_bottle > r_sweep, f"bottle {r_bottle:.0f} mm is inside the gun sweep {r_sweep:.0f} mm"
    eb = shapes["ebox_lid"].bounding_box()
    r_box = min(math.hypot(x - tm.PAN_X, y) for x in (eb.min.X, eb.max.X) for y in (eb.min.Y, eb.max.Y))
    assert r_box > r_sweep or eb.max.Z + 30 < zlow, "electronics box is inside the gun sweep"
    cr = shapes["cradle"].bounding_box()
    r_cradle = min(math.hypot(x - tm.PAN_X, y) for x in (cr.min.X, cr.max.X) for y in (cr.min.Y, cr.max.Y, 0) if cr.min.Y <= y <= cr.max.Y)
    assert r_cradle > r_sweep or cr.max.Z < zlow - 5, "cradle is inside the gun sweep"
    for (a, sa), (b, sb) in [(("tray", shapes["tray"]), ("cradle", shapes["cradle"])), (("tray", shapes["tray"]), ("ref_pump", ref["ref_pump"])),
                             (("cradle", shapes["cradle"]), ("ref_bottle", ref["ref_bottle"])), 
                             (("ebox", shapes["ebox"]), ("ebox_lid", shapes["ebox_lid"])), (("base_clamp", shapes["base_clamp"]), ("ref_rail_r", ref["ref_rail_r"]))]:
        v = (sa & sb).volume
        assert v < 1e-3, f"{a} overlaps {b} by {v:.2f} mm3"
    mod = {"deck": ts.PARTS["deck"](), "pan_base": ts.PARTS["pan_base"](), "ref_pan_servo": ts.refs()["ref_pan_servo"]}
    for bn in ("base_clamp", "base_tripod"):
        for mn, ms in mod.items():
            v = (shapes[bn] & ms).volume
            assert v < 1e-3, f"{bn} overlaps the module {mn} by {v:.2f} mm3"
    return {"gun_rear_low_z_mm": round(zlow, 1), "pump_top_z_mm": round(top, 1), "gun_sweep_r_mm": round(r_sweep, 1),
            "bottle_r_mm": round(r_bottle, 1)}


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shapes = {n: f() for n, f in PARTS.items()}
    ref = refs()
    info = {"h_base_mm": H_BASE, "parts": {}, "estop_xyz_mm": [BOX_AT[0] + ESTOP_XY[0], BOX_AT[1] + ESTOP_XY[1], Z_TABLE + BOX_FLOOR + BOX_IN[2] + 3],
            "bottle_xy_mm": list(BOTTLE_XY), "bottle_top_z_mm": TRAY_Z0 + bp.CR_WALL + bp.TANK_H,
            "pump_xyz_mm": [PUMP_XC, PUMP_YC, TRAY_Z0 + PUMP_BOSS + bp.PUMP_H / 2]}
    for n, s in shapes.items():
        export_step(s, str(OUT / f"{n}.step"))
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.02, angular_tolerance=0.1)
        g, gs = tm.mass(s)
        w = tm.wall_scan(OUT / f"{n}.stl")
        bb = s.bounding_box()
        info["parts"][n] = {"volume_cm3": round(s.volume / 1000, 1), "mass_g": round(g), "mass_solid_g": round(gs),
                            "bbox_mm": [round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)], "min_wall_scan_mm": round(w, 2)}
        print(f"{n:12s} V={s.volume / 1000:6.1f} cm3  m~{g:4.0f} g  wall {w:.2f}  bbox {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f}")
        # The backpack cradle (imported unchanged) has knife-edge tips where its cup wall ends: see README.
        assert w >= 1.95 or n == "cradle", f"{n}: thinnest wall found {w:.2f} mm"
    (OUT / "ref").mkdir(exist_ok=True)
    for n, s in ref.items():
        export_stl(s, str(OUT / "ref" / f"{n}.stl"), tolerance=0.05, angular_tolerance=0.2)
    info["clearance"] = check(shapes, ref)
    info["stability"] = stability(shapes, ref)
    print(json.dumps(info["clearance"]), "\n", json.dumps(info["stability"]))
    (OUT / "bench.json").write_text(json.dumps(info, indent=1))
    print("checks passed")
