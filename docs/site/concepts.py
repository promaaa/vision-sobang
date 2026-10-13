"""Write site/concepts/index.html, the body concepts article."""
import sys

C = [
    ("A", "Water gun turret",
     "An electric toy water gun sits on a two-servo pan-tilt mount on top of the torso. The gun keeps its own tank and pump. We remove the handle and connect the trigger to a relay. A USB camera sits on the gun, so the image shows where the water goes.",
     [("Water", "Gun tank, about 0.5 L"), ("Aim", "Pan-tilt, 2 servos"), ("Added mass", "~1.4 kg"), ("Build effort", "Low")],
     ["Fastest and cheapest build. No pump or hoses to design.", "Good first demonstration while the walking work goes on."],
     ["Short range and low flow.", "The gun sits high, so the centre of mass goes up."]),
    ("B", "Backpack pump",
     "A tank and a 12 V diaphragm pump sit on a back frame. The head carries the cameras and the nozzle. The nozzle is fixed under the cameras, so the robot sprays where it looks. After one calibration, the centre of the camera image is the aim point. The pump sits above the tank and primes itself.",
     [("Water", "1.4 L tank on the back"), ("Aim", "Head pan-tilt, 2 servos"), ("Added mass", "~2.7 kg"), ("Build effort", "Medium")],
     ["More water and more pressure than A.", "One aim system for vision and water."],
     ["The water on the back moves the centre of mass backward. The walking policy must learn this load.", "The water moves in the tank while the robot walks."]),
    ("C", "Arm lance",
     "This is the full Berkeley Humanoid Lite with arms. The right arm holds a nozzle lance, and the head carries a helmet with cameras. The arm already exists in the Berkeley design, with 5 motors. The hose runs from the backpack pump over the right shoulder and along the arm. The left arm can help with balance.",
     [("Water", "1.0 L backpack tank and pump"), ("Aim", "Right arm, 5 motors"), ("Added mass", "~2.3 kg + 5.0 kg of arms"), ("Build effort", "High")],
     ["Most human-like. Best for a presentation.", "The arm can aim in many directions and around obstacles."],
     ["Heaviest concept, about 18.6 kg.", "The arm must hold the lance against the push of the water jet.", "Most control work: arm and balance together."]),
    ("D", "Sealed shell",
     "A reflective shell covers the torso. The nozzle is fixed in the chest, and the robot aims with its whole body. The tank, pump, battery and computer are inside the shell. The robot turns with its hip motors to aim left and right, and bends its legs to aim up and down. A gauge on the side shows the water level.",
     [("Water", "About 1 L inside the shell"), ("Aim", "Whole body, no extra motors"), ("Added mass", "~2.3 kg"), ("Build effort", "Medium to high")],
     ["Protects the electronics from water and heat.", "No extra motors that can break. Carry handle on top."],
     ["Slow and coarse aim. The robot must stop and turn to aim.", "The shell needs air vents for the electronics."]),
    ("E", "Tethered hose",
     "There is no water on board. A hose from an external pump or a tap connects to the back of the pelvis. A solenoid valve on the pan-tilt mount opens the nozzle. The camera sits on a short mast. A power cable can run next to the hose, so the robot can also run without a battery.",
     [("Water", "No limit, from outside"), ("Aim", "Pan-tilt, 2 servos"), ("Added mass", "~1.0 kg + hose pull"), ("Build effort", "Low to medium")],
     ["Lightest robot. No limit on water or run time.", "An outside pump can give real hose pressure."],
     ["The hose pulls the robot back and can catch the legs.", "The hose length limits the range, and the hose twists when the robot turns."]),
]


def block(k, name, text, facts, pros, cons):
    imgs = "\n".join(
        f'  <figure class="thumb"><a href="concept_{k}_{v}.jpg"><img src="concept_{k}_{v}.jpg" width="1200" height="1500" '
        f'alt="Concept {k}, {cap.lower()}" loading="lazy"></a><figcaption>{cap}</figcaption></figure>'
        for v, cap in (("front", "Front"), ("rear", "Rear"), ("detail", "Close-up of the top")))
    rows = "\n".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in facts)
    li = lambda xs: "\n".join(f"  <li>{x}</li>" for x in xs)
    return f'''<h3 id="{k.lower()}">Concept {k}: {name}</h3>
<p>{text}</p>
<div class="gallery">
{imgs}
</div>
<div class="scroll"><table>
{rows}
</table></div>
<p><b>Advantages</b></p>
<ul>
{li(pros)}
</ul>
<p><b>Disadvantages</b></p>
<ul>
{li(cons)}
</ul>
'''


toc = "\n".join(f'        <li><a href="#{k.lower()}"><span class="n">3.{i}</span>{k}: {n}</a></li>' for i, (k, n, *_) in enumerate(C, 1))
body = "\n".join(block(*c) for c in C)
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Body concepts</title>
<meta name="description" content="Five ways to add a water system to the Berkeley Humanoid Lite legs, with renders and a comparison.">
<link rel="stylesheet" href="../wiki.css">
</head>
<body>
<header class="topbar"><div>
  <a class="name" href="../">Firefighter robot</a>
  <nav><a href="../">Progress</a><a href="./" aria-current="page">Body concepts</a><a href="../torso-pump/">Torso pump</a><a href="../#files">Files</a><a href="https://github.com/promaaa/vision-sobang">Code</a></nav>
</div></header>

<div class="page">
<nav class="toc" aria-label="Contents">
  <h2>Contents</h2>
  <ol>
    <li><a href="#top">(Top)</a></li>
    <li><a href="#overview"><span class="n">1</span>Overview</a></li>
    <li><a href="#base"><span class="n">2</span>Shared base</a></li>
    <li><a href="#concepts"><span class="n">3</span>Concepts</a>
      <ol>
{toc}
      </ol></li>
    <li><a href="#comparison"><span class="n">4</span>Comparison</a></li>
    <li><a href="#choice"><span class="n">5</span>Suggested first build</a></li>
    <li><a href="#renders"><span class="n">6</span>Notes on the renders</a></li>
  </ol>
</nav>

<article id="top">
<h1>Body concepts</h1>
<p class="subtitle">Design review. First written on 7 October 2026. Last edited on 11 October 2026.</p>

<div class="related">
  <b>Related articles</b>
  <ul>
    <li><a href="../">Firefighter robot (progress)</a></li>
    <li><a href="https://github.com/HybridRobotics/berkeley-humanoid-lite-assets">Berkeley Humanoid Lite assets</a></li>
  </ul>
</div>

<p>We want a robot that walks to a fire and puts it out with a water nozzle or, as a fallback, a water gun. The body reuses the legs and the torso frame of the open-source Berkeley Humanoid Lite. This article shows five ways to add the water system, the cameras and the aiming. Each concept is drawn fully assembled, so we can compare them before we buy parts.</p>
<p>The concepts differ in three choices: where the water comes from, how the robot aims, and what sits on top of the hips.</p>
<div class="box note"><b>Note:</b> Status: <i>planned</i>. Nothing is built. All added masses are estimates.</div>

<h2 id="overview">Overview</h2>
<figure class="thumb">
  <a href="lineup.jpg"><img src="lineup.jpg" width="2400" height="1200" alt="Five robot concepts side by side" loading="lazy"></a>
  <figcaption>From left to right: A water gun turret, B backpack pump, C arm lance, D sealed shell, E tethered hose.</figcaption>
</figure>

<h2 id="base">Shared base</h2>
<p>All five concepts stand on the Berkeley Humanoid Lite legs: 6 motors per leg and about 0.8 m tall. In the robot's URDF file, the legs and the torso frame weigh 11.3 kg. Concept C also keeps the two arms.</p>
<p>Concepts B to E carry an RGB camera and a small thermal camera side by side. Concept A has a single RGB camera fixed on the gun.</p>

<h2 id="concepts">Concepts</h2>
{body}
<h2 id="comparison">Comparison</h2>
<div class="scroll"><table class="wide">
<tr><th>Concept</th><th>Water</th><th>Aim</th><th>New motors</th><th class="r">Added mass</th><th class="r">Total mass</th><th>Build effort</th></tr>
<tr><td>A</td><td>Gun tank, ~0.5 L</td><td>Pan-tilt</td><td>2 servos</td><td class="r">~1.4 kg</td><td class="r">~12.7 kg</td><td>Low</td></tr>
<tr><td>B</td><td>1.4 L tank and pump</td><td>Head pan-tilt</td><td>2 servos</td><td class="r">~2.7 kg</td><td class="r">~14.0 kg</td><td>Medium</td></tr>
<tr><td>C</td><td>1.0 L tank and pump</td><td>Right arm</td><td>0 (the arm has 5)</td><td class="r">~7.3 kg</td><td class="r">~18.6 kg</td><td>High</td></tr>
<tr><td>D</td><td>~1 L inside</td><td>Whole body</td><td>0</td><td class="r">~2.3 kg</td><td class="r">~13.6 kg</td><td>Medium to high</td></tr>
<tr><td>E</td><td>External, no limit</td><td>Pan-tilt</td><td>2 servos</td><td class="r">~1.0 kg</td><td class="r">~12.3 kg</td><td>Low to medium</td></tr>
<caption>Total mass = 11.3 kg for the legs and torso frame (from the URDF) plus the added parts. For C, the added mass includes 5.0 kg of arms and shoulder motors.</caption>
</table></div>

<h2 id="choice">Suggested first build</h2>
<p>Build concept A first. It needs the least new work and gives an early demonstration. Its top plate takes the head of B or the valve of E later.</p>
<p>The simulation results since 7 October support this choice. With the real CAD parts, the worst leg torque for A is 5.2 Nm, under the 6 Nm policy limit. The official walking policy walks with A at 6 Nm. See <a href="../#payload">Payload on the legs</a> and <a href="../#walking">Walking</a> in the progress article.</p>

<h2 id="renders">Notes on the renders</h2>
<p>The renders come from Blender 5.2 (Cycles). The legs, the torso and the arms are the real Berkeley Humanoid Lite meshes, placed from the URDF in the default standing pose: hip −0.2 rad, knee 0.4 rad, ankle −0.3 rad. The gun, tanks, pumps, heads and shell are simple placeholder shapes with approximate sizes. Click an image to open it at full size.</p>

<footer>
  <p>This page was last edited on 11 October 2026.</p>
  <p>Robot models and meshes: <a href="https://github.com/HybridRobotics/berkeley-humanoid-lite-assets">HybridRobotics/berkeley-humanoid-lite-assets</a>, licence CC BY-SA 4.0.</p>
</footer>
</article>
</div>
</body>
</html>
'''
open(sys.argv[1], "w", encoding="utf-8").write(page)
