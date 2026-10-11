# Turntable videos

`concept_A_turntable.mp4` shows concept A: the robot with the STS3215 module, the gun stand-in and the splash guard. `bench_turntable.mp4` shows the bench rig. Each `.jpg` is frame 1 of its video.
Each video is one full turn: 144 frames, 6 s at 24 fps, 1280 x 720, H.264. Blender rendered them with Cycles at 12 samples and the OptiX denoiser, in the dark studio of `cad/bhl.py`.
`turntable.py` builds the scenes with `cad/parts/render_module.py` and `cad/bench/render.py`. It does not copy them.
To render again, run this from the repository root (about 20 min per video while the GPU is shared): `blender -b --factory-startup -P cad/turntable/turntable.py -- third_party/berkeley-humanoid-lite-assets/data/robots/berkeley_humanoid/berkeley_humanoid_lite cad/turntable`
Add `concept_A` or `bench` at the end to render only one video. `TT_FRAMES=3` renders a short test, and ffmpeg must be installed.
