#### Statics: torques in slow poses (same method as rounds 1 to 3)

| Model | Add-on mass (kg) | CoM height (m) | CoM fore-aft / sideways (mm) | Stand peak (Nm) | Crouch peak (Nm) | Single-leg pitch peak (Nm) | Single-leg peak, all joints (Nm) |
|---|---|---|---|---|---|---|---|
| bare biped | 0.00 | 0.362 | -2 / +0 | 1.5 | 2.7 | 4.3 | 7.8 |
| A_real: water gun on the pan-tilt | 1.54 | 0.425 | -0 / -0 | 1.9 | 3.3 | 5.2 | 8.6 |
| B_real: backpack + Seaflo pump, full | 2.76 | 0.429 | -15 / +3 | 1.6 | 3.2 | 3.9 | 9.6 |
| B_real, empty | 1.81 | 0.411 | -8 / -1 | 1.5 | 2.9 | 4.4 | 8.9 |
| R1: tank inside the torso, full | 1.65 | 0.413 | +3 / +0 | 2.1 | 3.5 | 5.7 | 8.8 |
| R1, half | 1.34 | 0.405 | +2 / +0 | 2.0 | 3.4 | 5.4 | 8.6 |
| R1, empty | 1.02 | 0.397 | +1 / +0 | 1.9 | 3.2 | 5.1 | 8.4 |
| R2: side tanks, full | 1.92 | 0.410 | +3 / -0 | 2.2 | 3.6 | 5.8 | 8.9 |
| R2, half | 1.56 | 0.403 | +2 / -0 | 2.1 | 3.4 | 5.5 | 8.7 |
| R2, empty | 1.20 | 0.397 | +1 / -0 | 2.0 | 3.3 | 5.3 | 8.5 |

#### Walking with the shipped BHL policy, 20 s, training noise

| Model | stand, 6 Nm | vx 0.3, 6 Nm | vx 0.2 + yaw 0.5, 6 Nm | stand, 4 Nm | vx 0.3, 4 Nm | vx 0.2 + yaw 0.5, 4 Nm |
|---|---|---|---|---|---|---|
| bare biped | stands | +0.29 m/s | +0.19 m/s, +0.50 rad/s | stands | +0.17 m/s | +0.09 m/s, +0.38 rad/s |
| A_real: water gun on the pan-tilt | stands | +0.29 m/s | +0.17 m/s, +0.49 rad/s | stands | falls at 9.1 s | falls at 9.6 s |
| B_real: backpack + Seaflo pump, full | stands | +0.20 m/s | +0.08 m/s, +0.35 rad/s | falls at 0.9 s | falls at 0.8 s | falls at 0.8 s |
| B_real, empty | stands | +0.25 m/s | +0.10 m/s, +0.37 rad/s | stands | falls at 4.8 s | falls at 4.9 s |
| R1: tank inside the torso, full | stands | +0.30 m/s | +0.17 m/s, +0.51 rad/s | stands | falls at 18.0 s | falls at 6.4 s |
| R1, half | stands | +0.29 m/s | +0.16 m/s, +0.47 rad/s | stands | +0.18 m/s | +0.10 m/s, +0.34 rad/s |
| R1, empty | stands | +0.30 m/s | +0.19 m/s, +0.52 rad/s | stands | +0.18 m/s | +0.11 m/s, +0.36 rad/s |
| R2: side tanks, full | stands | +0.29 m/s | +0.18 m/s, +0.53 rad/s | stands | falls at 8.6 s | falls at 3.8 s |
| R2, half | stands | +0.29 m/s | +0.18 m/s, +0.52 rad/s | stands | +0.14 m/s | falls at 14.5 s |
| R2, empty | stands | +0.29 m/s | +0.18 m/s, +0.51 rad/s | stands | +0.19 m/s | +0.11 m/s, +0.37 rad/s |
| R1_half_slosh_nobaffle | stands | +0.29 m/s | +0.19 m/s, +0.52 rad/s | stands | +0.19 m/s | falls at 18.8 s |
| R1_half_slosh_baffle | stands | +0.30 m/s | +0.19 m/s, +0.53 rad/s | stands | +0.18 m/s | +0.11 m/s, +0.30 rad/s |
| R2_half_slosh_nobaffle | stands | +0.29 m/s | +0.19 m/s, +0.52 rad/s | stands | +0.16 m/s | falls at 6.8 s |
| R2_half_slosh_baffle | stands | +0.29 m/s | +0.18 m/s, +0.51 rad/s | stands | falls at 4.8 s | falls at 14.2 s |

Speeds are the mean forward speed and yaw rate from 5 to 20 s.

#### Largest push the policy survives (N s, 0.1 s on the torso, worst of 3 gait phases, 6 Nm)

| Model | standing: forward | standing: back | standing: left | standing: right | walking 0.3 m/s: forward | walking 0.3 m/s: back | walking 0.3 m/s: left | walking 0.3 m/s: right |
|---|---|---|---|---|---|---|---|---|
| bare biped | 7.5 | 4.5 | 3.8 | 3.8 | 6.0 | 7.9 | 1.9 | 2.6 |
| A_real: water gun on the pan-tilt | 9.4 | 4.5 | 4.1 | 4.1 | 8.6 | 7.9 | 2.6 | 3.8 |
| B_real: backpack + Seaflo pump, full | 5.6 | 3.4 | 4.5 | 4.5 | 8.6 | 4.5 | 2.6 | 2.6 |
| B_real, empty | 9.8 | 4.1 | 4.1 | 4.1 | 8.6 | 6.8 | 2.2 | 3.0 |
| R1: tank inside the torso, full | 8.6 | 4.9 | 4.1 | 4.1 | 7.5 | 7.9 | 2.6 | 3.4 |
| R1, half | 9.0 | 5.2 | 4.5 | 4.1 | 7.9 | 7.1 | 2.6 | 3.4 |
| R1, empty | 8.6 | 5.2 | 4.1 | 3.8 | 7.5 | 7.1 | 2.6 | 3.0 |
| R2: side tanks, full | 9.0 | 5.2 | 4.1 | 4.1 | 7.1 | 9.8 | 2.6 | 3.4 |
| R2, half | 8.6 | 5.2 | 4.1 | 4.1 | 7.5 | 8.2 | 2.6 | 3.0 |
| R2, empty | 8.2 | 5.2 | 4.1 | 3.8 | 7.9 | 7.5 | 2.6 | 2.6 |
| R1_half_slosh_nobaffle | 8.6 | 5.2 | 4.1 | 4.1 | 7.5 | 7.5 | 2.6 | 3.0 |
| R1_half_slosh_baffle | 9.0 | 5.2 | 4.1 | 4.1 | 7.9 | 7.1 | 2.6 | 3.4 |
| R2_half_slosh_nobaffle | 8.6 | 5.2 | 4.1 | 4.1 | 7.5 | 8.2 | 2.6 | 3.0 |
| R2_half_slosh_baffle | 8.6 | 5.2 | 4.1 | 4.1 | 7.5 | 7.9 | 2.2 | 3.0 |

#### Slosh model (half-full tanks)

| Model / tank | Water (kg) | Fill depth (mm) | Slosh mass (kg, share) | Slosh frequency x / y (Hz) |
|---|---|---|---|---|
| R1_half_slosh_nobaffle/water_0 | 0.316 | 26 | 0.223 (71 %) | 2.0 / 1.9 |
| R1_half_slosh_baffle/water_0 | 0.316 | 26 | 0.123 (39 %) | 5.1 / 4.3 |
| R2_half_slosh_nobaffle/water_0 | 0.181 | 44 | 0.108 (60 %) | 2.2 / 4.4 |
| R2_half_slosh_nobaffle/water_1 | 0.181 | 44 | 0.108 (60 %) | 2.2 / 4.4 |
| R2_half_slosh_baffle/water_0 | 0.181 | 44 | 0.044 (24 %) | 5.0 / 4.4 |
| R2_half_slosh_baffle/water_1 | 0.181 | 44 | 0.044 (24 %) | 5.0 / 4.4 |

| Model | Command | Slosh travel x, RMS / peak (mm) | Slosh travel y, RMS / peak (mm) |
|---|---|---|---|
| R1_half_slosh_nobaffle | vx 0.3 | 7.6 / 23.4 | 12.3 / 31.7 |
| R1_half_slosh_nobaffle | vx 0.2 + yaw 0.5 | 12.9 / 31.0 | 17.1 / 32.7 |
| R1_half_slosh_baffle | vx 0.3 | 2.0 / 8.4 | 2.4 / 8.5 |
| R1_half_slosh_baffle | vx 0.2 + yaw 0.5 | 1.8 / 7.9 | 2.9 / 9.5 |
| R2_half_slosh_nobaffle | vx 0.3 | 3.7 / 11.2 | 1.5 / 5.9 |
| R2_half_slosh_nobaffle | vx 0.2 + yaw 0.5 | 5.4 / 24.1 | 1.7 / 6.6 |
| R2_half_slosh_baffle | vx 0.3 | 0.7 / 2.4 | 0.5 / 1.9 |
| R2_half_slosh_baffle | vx 0.2 + yaw 0.5 | 0.8 / 2.5 | 0.9 / 3.0 |

#### Jet of the TCS M400K-V at 12 V (estimate, no air drag)

| Nozzle (mm) | Flow (L/min) | Exit speed (m/s) | Range to the floor from 0.9 m, no drag (m) |
|---|---|---|---|
| 1.0 | 0.31 | 6.6 | 5.3 |
| 1.5 | 0.53 | 5.0 | 3.3 |
| 2.0 | 0.67 | 3.5 | 2.0 |
| 2.5 | 0.74 | 2.5 | 1.2 |
| 3.0 | 0.77 | 1.8 | 0.8 |
