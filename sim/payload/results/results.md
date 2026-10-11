| Model | Total mass (kg) | CoM height (m) | CoM fore-aft offset (mm, + = forward) | Stand peak (Nm, joint) | Crouch peak (Nm, joint) | Single-leg peak, all joints (Nm, joint) | Single-leg peak, pitch joints (Nm, joint) | Margin to 6 Nm, single-leg pitch (Nm) | Margin to 20 Nm, single-leg all (Nm) |
|---|---|---|---|---|---|---|---|---|---|
| biped (no payload) | 11.34 | 0.362 | -2 | 1.5 (left_ankle_pitch) | 2.7 (left_ankle_pitch) | 7.8 (right_hip_roll) | 4.3 (right_ankle_pitch) | +1.7 | +12.2 |
| A water gun | 12.78 | 0.421 | +6 | 2.3 (left_ankle_pitch) | 3.6 (left_ankle_pitch) | 8.6 (right_hip_roll) | 5.9 (right_ankle_pitch) | +0.1 | +11.4 |
| B backpack, full | 14.04 | 0.427 | -16 | 1.6 (left_knee_pitch) | 3.2 (left_knee_pitch) | 9.3 (right_hip_roll) | 3.6 (right_ankle_pitch) | +2.4 | +10.7 |
| B backpack, empty | 12.64 | 0.402 | -5 | 1.6 (left_ankle_pitch) | 2.9 (left_ankle_pitch) | 8.5 (right_hip_roll) | 4.5 (right_ankle_pitch) | +1.5 | +11.5 |
| full robot with arms (no payload) | 16.33 | 0.449 | +30 | 5.0 (left_ankle_pitch) | 6.8 (left_ankle_pitch) | 11.5 (right_ankle_pitch) | 11.5 (right_ankle_pitch) | -5.5 | +8.5 |
| C arms + backpack, full | 18.65 | 0.479 | +22 | 5.0 (left_ankle_pitch) | 7.0 (left_ankle_pitch) | 12.4 (right_hip_roll) | 11.6 (right_ankle_pitch) | -5.6 | +7.6 |
| C arms + backpack, empty | 17.70 | 0.471 | +29 | 5.4 (left_ankle_pitch) | 7.3 (left_ankle_pitch) | 12.3 (right_ankle_pitch) | 12.3 (right_ankle_pitch) | -6.3 | +7.7 |
| D shell, full | 13.67 | 0.409 | +3 | 2.3 (left_ankle_pitch) | 3.7 (left_ankle_pitch) | 9.2 (right_hip_roll) | 6.0 (right_ankle_pitch) | +0.0 | +10.8 |
| D shell, empty | 12.67 | 0.395 | +2 | 2.0 (left_ankle_pitch) | 3.4 (left_ankle_pitch) | 8.6 (right_hip_roll) | 5.4 (right_ankle_pitch) | +0.6 | +11.4 |
| E tether, 5 N drag | 12.39 | 0.399 | +1 | 1.1 (left_knee_pitch) | 2.3 (left_knee_pitch) | 8.2 (right_hip_roll) | 3.1 (right_ankle_pitch) | +2.9 | +11.8 |
| E tether, 20 N drag | 12.39 | 0.399 | +1 | 3.2 (left_knee_pitch) | 4.4 (left_knee_pitch) | 7.3 (right_hip_roll) | 5.2 (right_knee_pitch) | +0.8 | +12.7 |

Centre of pressure outside a foot (pose not statically possible): none.

Peak arm joint torque in the stand pose, arms in ARM_POSE:

- full robot with arms (no payload): 2.8 Nm
- C arms + backpack, full: 3.4 Nm
- C arms + backpack, empty: 3.4 Nm

| Model | kp 20 / kd 2 / 6 Nm | kp 20 / kd 2 / 20 Nm | kp 50 / kd 2 / 6 Nm | kp 50 / kd 2 / 20 Nm | kp 200 / kd 5 / 6 Nm | kp 200 / kd 5 / 20 Nm | Push fwd / back (N s), kp 50 / kd 2 / 20 Nm | Push fwd / back (N s), kp 200 / kd 5 / 6 Nm | Push fwd / back (N s), kp 200 / kd 5 / 20 Nm |
|---|---|---|---|---|---|---|---|---|---|
| biped (no payload) | falls at 1.1 s | falls at 1.1 s | stands, 2.1 Nm | stands, 2.1 Nm | stands, 1.6 Nm | stands, 1.6 Nm | 4.1 / 4.5 | 4.1 / 5.0 | 5.2 / 5.0 |
| A water gun | falls at 0.8 s | falls at 0.8 s | falls at 1.5 s | stands, 5.1 Nm | stands, 2.6 Nm | stands, 2.6 Nm | 2.2 / 5.9 | 3.4 / 5.0 | 5.6 / 6.7 |
| B backpack, full | falls at 1.3 s | falls at 1.3 s | stands, 2.6 Nm | stands, 2.6 Nm | stands, 1.7 Nm | stands, 1.7 Nm | 6.1 / 3.3 | 4.8 / 5.5 | 7.2 / 5.5 |
| B backpack, empty | falls at 1.2 s | falls at 1.2 s | stands, 2.5 Nm | stands, 2.5 Nm | stands, 1.7 Nm | stands, 1.7 Nm | 4.4 / 5.2 | 4.2 / 5.5 | 6.1 / 5.6 |
| full robot with arms (no payload) | falls at 0.5 s | falls at 0.5 s | falls at 0.6 s | falls at 0.6 s | falls at 0.8 s | stands, 6.4 Nm | 0.0 / 0.0 | 0.0 / 0.0 | 3.6 / 6.7 |
| C arms + backpack, full | falls at 0.6 s | falls at 0.6 s | falls at 0.7 s | falls at 0.6 s | falls at 0.9 s | stands, 6.7 Nm | 0.0 / 0.0 | 0.0 / 0.0 | 5.0 / 7.7 |
| C arms + backpack, empty | falls at 0.5 s | falls at 0.5 s | falls at 0.6 s | falls at 0.6 s | falls at 0.8 s | stands, 7.1 Nm | 0.0 / 0.0 | 0.0 / 0.0 | 3.9 / 6.9 |
| D shell, full | falls at 0.8 s | falls at 0.8 s | falls at 1.7 s | stands, 4.9 Nm | stands, 2.6 Nm | stands, 2.6 Nm | 3.0 / 6.2 | 3.3 / 4.7 | 5.8 / 6.6 |
| D shell, empty | falls at 0.8 s | falls at 0.8 s | stands, 3.7 Nm | stands, 3.7 Nm | stands, 2.2 Nm | stands, 2.2 Nm | 3.8 / 5.8 | 3.6 / 4.8 | 5.5 / 5.9 |
| E tether, 5 N drag | falls at 6.4 s | falls at 6.4 s | stands, 1.2 Nm | stands, 1.2 Nm | stands, 1.1 Nm | stands, 1.1 Nm | 5.8 / 3.9 | 5.0 / 4.7 | 6.2 / 4.7 |
| E tether, 20 N drag | falls at 0.6 s | falls at 0.6 s | falls at 0.8 s | falls at 0.8 s | falls at 1.6 s | falls at 1.6 s | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |

"stands, X Nm": the robot stays up for 10 s. X is the peak leg torque in the last 2 s. Push values: the largest impulse on the torso (0.1 s) with no fall in the next 3 s. 0 means that the model does not stand.

Mass budget: extra point mass at the torso top centre (x 0, z 0.791), robot frame, on the biped:

| Added mass (kg) | Stand peak (Nm) | Crouch peak (Nm) | Single-leg peak, pitch joints (Nm) | Single-leg peak, all joints (Nm) |
|---|---|---|---|---|
| 0 | 1.5 | 2.7 | 4.3 | 7.8 |
| 2 | 2.3 | 3.7 | 6.0 | 8.9 |
| 4 | 3.1 | 4.7 | 7.7 | 9.9 |
| 6 | 3.9 | 5.7 | 9.4 | 11.0 |
| 8 | 4.7 | 6.7 | 11.0 | 12.0 |
| 10 | 5.4 | 7.7 | 12.7 | 13.1 |

- stand: at or below 6 Nm up to 10 kg added
- stand: at or below 20 Nm up to 10 kg added
- crouch: above 6 Nm from 7.0 kg added
- crouch: at or below 20 Nm up to 10 kg added
- single-leg, pitch joints: above 6 Nm from 2.0 kg added
- single-leg, pitch joints: at or below 20 Nm up to 10 kg added
- single-leg, all joints: above 6 Nm already with 0 kg added
- single-leg, all joints: at or below 20 Nm up to 10 kg added

Mass budget: extra point mass at the backpack (x -0.145, z 0.64), robot frame, on the biped:

| Added mass (kg) | Stand peak (Nm) | Crouch peak (Nm) | Single-leg peak, pitch joints (Nm) | Single-leg peak, all joints (Nm) |
|---|---|---|---|---|
| 0 | 1.5 | 2.7 | 4.3 | 7.8 |
| 2 | 1.8 | 3.2 | 3.0 | 8.9 |
| 4 | 3.0 | 4.7 | 4.8 | 10.0 |
| 6 | 4.3 | 6.3 | 7.1 | 11.1 |
| 8 | 5.5 | 7.8 | 9.4 | 12.1 |
| 10 | 6.7 | 9.4 | 11.7 | 13.2 |

- stand: above 6 Nm from 9.0 kg added
- stand: at or below 20 Nm up to 10 kg added
- crouch: above 6 Nm from 6.0 kg added
- crouch: at or below 20 Nm up to 10 kg added
- single-leg, pitch joints: above 6 Nm from 5.5 kg added
- single-leg, pitch joints: at or below 20 Nm up to 10 kg added
- single-leg, all joints: above 6 Nm already with 0 kg added
- single-leg, all joints: at or below 20 Nm up to 10 kg added
