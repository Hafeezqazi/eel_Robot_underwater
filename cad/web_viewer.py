"""
web_viewer.py  --  Generate a self-contained browser 3-D viewer (three.js).

Tessellates every part of the robot in its LOCAL frame and writes a single
standalone HTML file (output/eel_viewer.html). Open it by double-click in any
modern browser -- no server needed. The forward-kinematics + gait are
replicated in JavaScript so the eel SWIMS live, and you can orbit / zoom,
slide the swim speed and dive-plane angle, and toggle the internal parts.

three.js loads from a CDN (needs internet the first time). Run:
    python web_viewer.py   ->  output/eel_viewer.html
"""

import os
import sys
import json
import cadquery as cq
import params as P

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "firmware"))
import gait
from body import driven_segments, servo_mock
from head_bay import build_head, build_lid
from joints import pin as joint_pin, servo_horn, band_post
import dive_planes
import internals
from assembly import tail_fin

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")

COL = {  # part -> hex colour
    "head": "#2e8b57", "lid": "#9aa0a6", "body": "#4682b4",
    "servo": "#6b6f76", "pin": "#ffd700", "plane": "#e08a00",
    "shaft": "#808890", "tail": "#2e8b57", "horn": "#d14fa0", "post": "#2f9e6e",
}


def to_mesh(shape, color, tol=0.6, translate=None, internal=False):
    if hasattr(shape, "val"):
        shape = shape.val()
    if translate is not None:
        shape = shape.translate(translate)
    verts, tris = shape.tessellate(tol)
    pos = []
    for v in verts:
        pos += [round(v.x, 2), round(v.y, 2), round(v.z, 2)]
    idx = []
    for t in tris:
        idx += [int(t[0]), int(t[1]), int(t[2])]
    return {"color": color, "pos": pos, "idx": idx, "internal": internal}


def build_data():
    servo = servo_mock()
    pinm = joint_pin()
    segs = driven_segments()

    data = {
        "params": {
            "HEAD_LEN": P.HEAD_LEN, "SEG_LEN": P.SEG_LEN, "N": P.N_JOINTS,
            "BODY_LENGTH": P.BODY_LENGTH, "DIVE_PLANE_Z": P.DIVE_PLANE_Z,
            "f": gait.tail_beat_freq(),
            "phi": gait.phase_lags(),                       # rad
            "amp": gait.amplitude_envelope(),               # deg
            "diveMax": P.DIVE_PLANE_MAX_DEG,
        },
        "base": [
            to_mesh(build_head(), COL["head"]),
            to_mesh(build_lid(), COL["lid"],
                    translate=(0, 0, P.HEAD_LEN - P.LID_LEN)),
        ],
        "dive": [
            to_mesh(dive_planes.plane(+1), COL["plane"]),
            to_mesh(dive_planes.plane(-1), COL["plane"]),
            to_mesh(dive_planes.shaft(), COL["shaft"], internal=True),
        ],
        "seg": [],
        "tail": [to_mesh(tail_fin(), COL["tail"])],
    }
    hornm, postm = servo_horn(), band_post(x=0, z=8)
    foam_plugs = internals.foam_plugs()               # [(z_centre, solid)]
    for i, (name, sol, part) in enumerate(segs):
        sm = [to_mesh(sol, COL["body"])]
        if part["driven"]:                            # servo + horn on driven joints
            sm.append(to_mesh(servo, COL["servo"], internal=True))
            sm.append(to_mesh(hornm, COL["horn"], internal=True))
        else:                                         # passive: rubber-band post
            sm.append(to_mesh(postm, COL["post"], internal=True))
        sm.append(to_mesh(pinm, COL["pin"], internal=True))
        # buoyancy foam discs sit in the bays that span their centre (local
        # frame) so they bend with that segment, not the base frame
        seg_front = P.HEAD_LEN + i * P.SEG_LEN
        for zc, fsol in foam_plugs:
            if seg_front <= zc < seg_front + P.SEG_LEN:
                sm.append(to_mesh(fsol, "#d8d8cf", internal=True,
                                  translate=(0, 0, zc - seg_front)))
        data["seg"].append(sm)
    data["bay"] = [to_mesh(s, c, internal=True)
                   for it, c, s in internals.components()]
    # dive servo fixed to the body (base frame), not the rotating dive group
    data["bay"].append(to_mesh(internals.dive_servo(), COL["servo"],
                               internal=True))
    return data


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eel Robot - 3D Viewer</title>
<style>
  html,body{margin:0;height:100%;background:#0f1419;color:#e6edf3;
    font-family:system-ui,Segoe UI,Arial,sans-serif;overflow:hidden}
  #c{position:fixed;inset:0}
  #ui{position:fixed;top:12px;left:12px;background:rgba(20,26,33,.82);
    padding:14px 16px;border-radius:10px;backdrop-filter:blur(4px);
    box-shadow:0 4px 18px rgba(0,0,0,.4);max-width:260px;font-size:13px}
  #ui h1{margin:0 0 8px;font-size:15px;font-weight:600}
  #ui .row{display:flex;align-items:center;justify-content:space-between;
    gap:8px;margin:7px 0}
  #ui label{flex:1}
  #ui input[type=range]{width:120px}
  #ui button{background:#2d6cdf;color:#fff;border:0;border-radius:6px;
    padding:6px 10px;cursor:pointer;font-size:12px}
  #ui button.sec{background:#2b333d}
  #legend{margin-top:8px;font-size:11px;line-height:1.7;color:#aeb6bf}
  .sw{display:inline-block;width:10px;height:10px;border-radius:2px;
    margin-right:6px;vertical-align:middle}
  #hint{position:fixed;bottom:10px;left:12px;font-size:11px;color:#7d868f}
  #depth{position:fixed;top:12px;right:12px;background:rgba(20,26,33,.82);
    padding:8px 12px;border-radius:8px;font-size:13px;font-weight:600;color:#cfe6ff}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="ui">
  <h1>Eel Robot &mdash; live</h1>
  <div class="row"><button id="play">&#10073;&#10073; Pause</button>
    <button id="spin" class="sec">Auto-spin</button></div>
  <div class="row"><label>Swim speed</label>
    <input id="speed" type="range" min="0" max="100" value="60"></div>
  <div class="row"><label>Dive plane</label>
    <input id="dive" type="range" min="-25" max="25" value="0"></div>
  <div class="row"><label>Show internals</label>
    <input id="intern" type="checkbox" checked></div>
  <div class="row"><button id="reset" class="sec">Reset view</button></div>
  <div id="legend">
    <div><span class="sw" style="background:#2e8b57"></span>head bay / tail fin</div>
    <div><span class="sw" style="background:#4682b4"></span>body segments (5 joints)</div>
    <div><span class="sw" style="background:#e08a00"></span>bow dive planes (depth)</div>
    <div><span class="sw" style="background:#6b6f76"></span>servos / shaft (internals)</div>
  </div>
</div>
<div id="hint">drag = orbit &nbsp;|&nbsp; scroll = zoom &nbsp;|&nbsp; right-drag = pan</div>
<div id="depth">Depth 0.00 m</div>

<script type="importmap">
{ "imports": {
  "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
  "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
}}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = /*DATA*/;
const PRM = DATA.params;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1419);
const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 1, 8000);
const renderer = new THREE.WebGLRenderer({canvas:document.getElementById('c'),
  antialias:true});
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio,2));

scene.add(new THREE.HemisphereLight(0xcfe6ff, 0x20262e, 1.05));
const dir = new THREE.DirectionalLight(0xffffff, 1.4);
dir.position.set(0.4, 1, 0.7); scene.add(dir);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
const CENTER = new THREE.Vector3(0, 0, PRM.BODY_LENGTH/2);
controls.target.copy(CENTER);

function makeMesh(m){
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(m.pos, 3));
  g.setIndex(m.idx);
  g.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({color:m.color, metalness:0.25,
    roughness:0.6, side:THREE.DoubleSide, transparent:true, opacity:1});
  const mesh = new THREE.Mesh(g, mat);
  mesh.userData.internal = !!m.internal;
  return mesh;
}

const robot = new THREE.Group();
scene.add(robot);

// depth environment: water surface + depth marker rings (world-fixed)
const env = new THREE.Group(); scene.add(env);
{ const s = new THREE.Mesh(new THREE.PlaneGeometry(2600,1500),
    new THREE.MeshBasicMaterial({color:0x2f5d86,transparent:true,opacity:0.16,
      side:THREE.DoubleSide}));
  s.rotation.x = -Math.PI/2; s.position.set(CENTER.x,0,CENTER.z); env.add(s); }
for(let d=0; d<=2500; d+=500){
  const g = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(CENTER.x-440,-d,CENTER.z-380),
    new THREE.Vector3(CENTER.x+440,-d,CENTER.z-380),
    new THREE.Vector3(CENTER.x+440,-d,CENTER.z+380),
    new THREE.Vector3(CENTER.x-440,-d,CENTER.z+380),
    new THREE.Vector3(CENTER.x-440,-d,CENTER.z-380)]);
  env.add(new THREE.Line(g, new THREE.LineBasicMaterial(
    {color: d===0 ? 0x4a90d9 : 0x33506b})));
}

// fixed base (head + lid) + electronics in the bay
DATA.base.forEach(m => robot.add(makeMesh(m)));
(DATA.bay||[]).forEach(m => robot.add(makeMesh(m)));

// dive planes group (pitch about X at DIVE_PLANE_Z)
const diveGroup = new THREE.Group();
diveGroup.position.set(0, 0, PRM.DIVE_PLANE_Z);
DATA.dive.forEach(m => diveGroup.add(makeMesh(m)));
robot.add(diveGroup);

// driven segment groups (FK chain)
const segGroups = DATA.seg.map(parts => {
  const grp = new THREE.Group();
  parts.forEach(m => grp.add(makeMesh(m)));
  robot.add(grp);
  return grp;
});
// tail group (rides on the chain end)
const tailGroup = new THREE.Group();
DATA.tail.forEach(m => tailGroup.add(makeMesh(m)));
robot.add(tailGroup);

const D2R = Math.PI/180;
function updatePose(t, speed){
  const f = PRM.f * speed;
  let px=0, pz=PRM.HEAD_LEN, theta=0;
  for(let i=0;i<PRM.N;i++){
    theta += PRM.amp[i]*D2R * Math.sin(2*Math.PI*f*t - PRM.phi[i]);
    const g = segGroups[i];
    g.position.set(px, 0, pz);
    g.rotation.set(0, theta, 0);
    px += Math.sin(theta)*PRM.SEG_LEN;
    pz += Math.cos(theta)*PRM.SEG_LEN;
  }
  tailGroup.position.set(px, 0, pz);
  tailGroup.rotation.set(0, theta, 0);
}

// UI state
let playing=true, spinning=false, speed=0.6, dive=0, t0=performance.now();
let depth=0, prevDepth=0;   // descent (scene mm)
const $ = id => document.getElementById(id);
$('play').onclick = e=>{ playing=!playing;
  e.target.innerHTML = playing ? '&#10073;&#10073; Pause' : '&#9654; Play';
  if(playing) t0 = performance.now() - tcur*1000; };
$('spin').onclick = e=>{ spinning=!spinning;
  e.target.style.background = spinning ? '#2d6cdf' : '#2b333d'; };
$('speed').oninput = e=> speed = e.target.value/100;
$('dive').oninput = e=> dive = +e.target.value;
function setInternals(show){ robot.traverse(o=>{ if(!o.isMesh) return;
  if(o.userData.internal) o.visible=show;
  else o.material.opacity = show ? 0.38 : 1.0; }); }
$('intern').onchange = e=> setInternals(e.target.checked);
$('reset').onclick = ()=>{depth=0;prevDepth=0;robot.position.set(0,0,0);robot.rotation.x=0;frame();};
setInternals(true);    // start showing internals (translucent body)

let tcur=0;
let lastT = performance.now();
function loop(){
  requestAnimationFrame(loop);
  const now = performance.now(); const dt = Math.min(0.05,(now-lastT)/1000); lastT=now;
  if(playing) tcur = (performance.now()-t0)/1000;
  updatePose(tcur, speed);
  diveGroup.rotation.x = -dive*D2R;     // +slider = dive (LE down)
  // DEPTH: descend/climb only while swimming; bow fins pitch the nose down/up
  depth += 420*(dive/25)*speed*dt;
  depth = Math.max(0, Math.min(2500, depth));
  const dd = depth-prevDepth; prevDepth=depth;
  const pitch = -(dive/25)*0.36*(speed>0.02?1:0);     // nose-down for dive
  const Cz = PRM.BODY_LENGTH/2;
  robot.rotation.x = pitch;
  robot.position.set(0, -depth + Cz*Math.sin(pitch), Cz*(1-Math.cos(pitch)));
  camera.position.y -= dd; controls.target.y -= dd;
  document.getElementById('depth').textContent = 'Depth '+(depth/1000).toFixed(2)+' m';
  if(spinning) robot.rotation.y += 0.004;
  controls.update();
  renderer.render(scene, camera);
}

function frame(){
  robot.rotation.y = 0;
  const d = PRM.BODY_LENGTH*1.5;
  camera.position.set(CENTER.x + d*0.28, CENTER.y + d*0.42, CENTER.z + d*0.9);
  controls.target.copy(CENTER);
  controls.update();
}
addEventListener('resize', ()=>{
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
frame();
loop();
</script>
</body>
</html>
"""


def main():
    data = build_data()
    html = HTML.replace("/*DATA*/", json.dumps(data, separators=(",", ":")))
    path = os.path.normpath(os.path.join(OUT, "eel_viewer.html"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    # mirror to the repo root so it opens straight from the main repo page
    root = os.path.normpath(os.path.join(OUT, "..", "eel_viewer.html"))
    with open(root, "w", encoding="utf-8") as fh:
        fh.write(html)
    ntri = sum(len(m["idx"]) // 3 for m in data["base"] + data["dive"]
               + data["tail"]) + sum(len(p["idx"]) // 3
                                     for s in data["seg"] for p in s)
    kb = os.path.getsize(path) / 1024
    print(f"[ok] {path}")
    print(f"     {ntri} triangles, {kb:.0f} KB self-contained HTML")
    print("     open in any browser (double-click). three.js loads from CDN.")


if __name__ == "__main__":
    main()
