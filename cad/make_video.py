"""
make_video.py  --  generate a HyperFrames composition (video/index.html) of the
eel swimming + diving, reusing the SAME 3D scene data the HTML viewer uses
(design_page.build_geo): real meshes, gait FK, internals, depth context.

Unlike the viewer (real-time, swims in place), this composition is SEEK-DRIVEN
(renders from HyperFrames time, per the `three` adapter) and adds what the GIF
was missing: forward travel (streaming bubbles + the travelling wave), a dive
that pitches nose-down and descends through depth rings, a see-through body so
the internals read, and timed captions.

Run:  python make_video.py   ->  ../video/index.html
Then: cd ../video && npx hyperframes render --output ../output/eel_demo.mp4
"""

import os
import json
import design_page

HERE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.normpath(os.path.join(HERE, "..", "video"))

DUR = 8.0          # seconds
W, H = 1280, 720

HTML = r"""<!doctype html>
<html data-fps="30">
<head>
<meta charset="utf-8">
<style>
  html,body{margin:0;background:#0d1117;overflow:hidden}
  #root{position:relative;width:100%;height:100%;
    background:radial-gradient(120% 120% at 50% 18%, #16314d 0%, #0c1320 55%, #070b12 100%);
    font-family:Inter, system-ui, sans-serif}
  #three-layer{position:absolute;inset:0;width:100%;height:100%;display:block}
  .ui{position:absolute;inset:0;pointer-events:none}
  .title{position:absolute;left:54px;top:44px}
  .title .h{font-size:40px;font-weight:800;color:#eaf2ff;letter-spacing:.2px;margin:0}
  .title .s{font-size:20px;color:#7fb2e6;margin:6px 0 0;font-weight:600}
  .cap{position:absolute;left:54px;bottom:52px;font-size:30px;font-weight:700;
    color:#dbe8f7;opacity:0}
  .cap .dot{color:#ff9a3c}
  .badge{position:absolute;right:50px;bottom:50px;font-size:16px;color:#6f8aa6;
    font-weight:600}
</style>
</head>
<body>
<div id="root" data-composition-id="root" data-start="0" data-width="__W__" data-height="__H__" data-duration="__DUR__">
  <canvas id="three-layer"></canvas>
  <div class="ui">
    <div class="title">
      <p class="h">Bio-Inspired Eel Robot</p>
      <p class="s">free-flooding body &middot; travelling-wave swim &middot; bow-plane dive</p>
    </div>
    <div class="cap" id="cap1"><span class="dot">&#9656;</span> Travelling-wave swim &mdash; thrust from the body, not a propeller</div>
    <div class="cap" id="cap2"><span class="dot">&#9656;</span> Bow planes pitch &mdash; nose-down dive through the depth rings</div>
    <div class="cap" id="cap3"><span class="dot">&#9656;</span> See-through body &mdash; battery, ESP32, foam &amp; keel inside</div>
    <div class="badge">predicted ~0.5 m/s &middot; 2 Hz tail-beat</div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    // overlay timeline (captions). Canvas is rendered by the three adapter.
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    tl.from(".title .h", {y:-24,opacity:0,duration:.7,ease:"power3.out"}, .15)
      .from(".title .s", {y:-16,opacity:0,duration:.6,ease:"power2.out"}, .35)
      .from(".badge",    {opacity:0,duration:.6}, .6);
    // three captions, one per beat, fade in then out (no overlap)
    const caps=[["#cap1",0.6,2.6],["#cap2",2.9,5.4],["#cap3",5.7,7.7]];
    caps.forEach(([sel,a,b])=>{
      tl.fromTo(sel,{opacity:0,y:18},{opacity:1,y:0,duration:.5,ease:"power2.out"},a);
      tl.to(sel,{opacity:0,duration:.45,ease:"power2.in"},b);
    });
    window.__timelines["root"] = tl;
  </script>

  <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
  <script>
    const DATA = __DATA__;
    const PRM = DATA.geo.params, D2R = Math.PI/180, DUR = __DUR__;

    const canvas = document.getElementById("three-layer");
    const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true});
    renderer.setSize(__W__, __H__, false); renderer.setPixelRatio(1);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, __W__/__H__, 1, 9000);
    scene.add(new THREE.HemisphereLight(0xcfe6ff,0x16314d,1.15));
    const dl = new THREE.DirectionalLight(0xffffff,1.4); dl.position.set(.4,1,.6); scene.add(dl);

    const CZ = PRM.BODY_LENGTH/2;
    const robot = new THREE.Group(); scene.add(robot);

    function mk(m){
      const g=new THREE.BufferGeometry();
      g.setAttribute('position',new THREE.Float32BufferAttribute(m.pos,3));
      g.setIndex(m.idx); g.computeVertexNormals();
      const body = !m.internal;
      const mat=new THREE.MeshStandardMaterial({color:m.color,metalness:.25,
        roughness:.62,side:THREE.DoubleSide,transparent:true,
        opacity: body?0.5:1.0, depthWrite: body?false:true});
      return new THREE.Mesh(g,mat);
    }
    DATA.geo.base.forEach(m=>robot.add(mk(m)));
    (DATA.geo.bay||[]).forEach(m=>robot.add(mk(m)));
    const diveG=new THREE.Group(); diveG.position.set(0,0,PRM.DIVE_PLANE_Z);
    DATA.geo.dive.forEach(m=>diveG.add(mk(m))); robot.add(diveG);
    const segG=DATA.geo.seg.map(parts=>{const g=new THREE.Group();
      parts.forEach(m=>g.add(mk(m))); robot.add(g); return g;});
    const tailG=new THREE.Group(); DATA.geo.tail.forEach(m=>tailG.add(mk(m))); robot.add(tailG);

    // ---- world-fixed depth rings (the dive descends through these) ----
    const env=new THREE.Group(); scene.add(env);
    for(let i=0;i<5;i++){ const d=i*70;
      const g=new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-260,-d,CZ-300),new THREE.Vector3(260,-d,CZ-300),
        new THREE.Vector3(260,-d,CZ+360),new THREE.Vector3(-260,-d,CZ+360),
        new THREE.Vector3(-260,-d,CZ-300)]);
      env.add(new THREE.Line(g,new THREE.LineBasicMaterial(
        {color:i===0?0x3f6f9f:0x274058,transparent:true,opacity:.8})));
    }
    // ---- streaming bubbles -> forward-motion cue (seeded, deterministic) ----
    function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);
      t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
    const rnd=mulberry32(7); const NB=70, BSPAN=900, bub=[];
    const bgeo=new THREE.SphereGeometry(2.1,8,8);
    const bmat=new THREE.MeshBasicMaterial({color:0x9fd2ff,transparent:true,opacity:.5});
    for(let i=0;i<NB;i++){ const m=new THREE.Mesh(bgeo,bmat);
      const seed=rnd()*BSPAN, x=(rnd()-0.5)*460, y=-(rnd()*300)+20;
      m.userData={seed,x,y}; scene.add(m); bub.push(m); }

    function pose(t){ let px=0,pz=PRM.HEAD_LEN,th=0; const f=PRM.f;
      for(let i=0;i<PRM.N;i++){ th+=PRM.amp[i]*D2R*Math.sin(2*Math.PI*f*t-PRM.phi[i]);
        segG[i].position.set(px,0,pz); segG[i].rotation.set(0,th,0);
        px+=Math.sin(th)*PRM.SEG_LEN; pz+=Math.cos(th)*PRM.SEG_LEN; }
      tailG.position.set(px,0,pz); tailG.rotation.set(0,th,0); return th; }

    function diveAmt(t){ // smooth 0->1->0 bump over 2.7..5.6 s
      const a=2.7,b=5.6; if(t<a||t>b) return 0;
      return 0.5-0.5*Math.cos(2*Math.PI*(t-a)/(b-a)); }

    function renderAt(time){
      const t=Math.max(0,Math.min(DUR,time));
      pose(t);
      const d=diveAmt(t);
      // dive: planes deflect (front of body), whole body pitches nose-down + sinks
      diveG.rotation.x = -D2R*22*d;
      robot.rotation.x = D2R*16*d;                 // nose-down
      robot.position.set(0, -150*d, 0);            // descend through rings
      // bubbles stream toward -Z (camera) -> reads as forward swimming
      for(const m of bub){ let z=CZ+360 - ((m.userData.seed + time*230)%BSPAN);
        m.position.set(m.userData.x, m.userData.y, z); }
      // steady 3/4 follow camera, easing down a touch during the dive
      const cy = 120 - 120*d, look=new THREE.Vector3(0,-150*d+30,CZ);
      camera.position.set(360, cy+150, CZ-470);
      camera.lookAt(look);
      renderer.render(scene,camera);
    }
    window.addEventListener("hf-seek",e=>renderAt(e.detail.time));
    renderAt(window.__hfThreeTime||0);
  </script>
</div>
</body>
</html>
"""


def main():
    os.makedirs(VID, exist_ok=True)
    geo = design_page.build_geo()
    data = json.dumps({"geo": geo}, separators=(",", ":"))
    html = (HTML.replace("__DATA__", data).replace("__DUR__", str(DUR))
            .replace("__W__", str(W)).replace("__H__", str(H)))
    out = os.path.join(VID, "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[ok] {out}  ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
