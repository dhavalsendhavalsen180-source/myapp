/* static/js/facefilter_pro.js
   FULL SNAP + REMINI + FaceMesh engine (WebGL2 friendly)
   Exports:
     - enableSnapRemini(options)
     - applyProFilter(name)
     - applyLUT(url)
*/

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.150.1/build/three.module.js";

let renderer, scene, camera, mesh, material;
let videoEl, gpuCanvas, videoTexture;
let neutralLUT = null;

/* default powers */
let DEFAULTS = {
  smooth: 0.55,
  clarity: 0.40,
  detail: 0.20,
  hdr: 0.20,
  lutStrength: 0.7
};

/* built-in presets (names used by HTML buttons) */
const PRESETS = {
  none: { smooth:0.0, clarity:0.0, detail:0.0, hdr:0.0, lut: null },
  beauty: { smooth:0.55, clarity:0.45, detail:0.18, hdr:0.12, lut: null },
  snapWarm: { smooth:0.45, clarity:0.55, detail:0.20, hdr:0.18, lut:'/static/luts/snap_warm.png' },
  snapCool: { smooth:0.45, clarity:0.5, detail:0.18, hdr:0.16, lut:'/static/luts/snap_cool.png' },
  cinematic: { smooth:0.28, clarity:0.65, detail:0.2, hdr:0.22, lut:'/static/luts/cinematic.png' },
  vintage: { smooth:0.2, clarity:0.2, detail:0.08, hdr:0.06, lut:'/static/luts/vintage.png' },
  neon: { smooth:0.25, clarity:0.75, detail:0.3, hdr:0.22, lut:'/static/luts/neon.png' },
  instagram: { smooth:0.5, clarity:0.55, detail:0.2, hdr:0.15, lut:'/static/luts/insta.png' },
  tiktok: { smooth:0.7, clarity:0.7, detail:0.25, hdr:0.2, lut:'/static/luts/tiktok.png' },
  hdr: { smooth:0.2, clarity:0.8, detail:0.3, hdr:0.35, lut:null },
  nightVision: { smooth:0.4, clarity:0.6, detail:0.18, hdr:0.05, lut:'/static/luts/night.png' },
  fire: { smooth:0.3, clarity:0.5, detail:0.2, hdr:0.18, lut:'/static/luts/fire.png' },
  icy: { smooth:0.35, clarity:0.45, detail:0.18, hdr:0.12, lut:'/static/luts/ice.png' },
  retro: { smooth:0.25, clarity:0.25, detail:0.1, hdr:0.06, lut:'/static/luts/retro.png' }
};

/* create neutral LUT texture */
function makeNeutralLUT(){
  const tex = new THREE.DataTexture(new Uint8Array([255,255,255]), 1,1, THREE.RGBFormat);
  tex.needsUpdate = true;
  return tex;
}

/* Build shader material (WebGL2 style shader using texture()) */
function buildMaterial(videoTex, w=1280, h=720){
  const mat = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3,
    uniforms: {
      frame: { value: videoTex },
      lutTex: { value: neutralLUT },
      smooth: { value: DEFAULTS.smooth },
      clarity: { value: DEFAULTS.clarity },
      detail: { value: DEFAULTS.detail },
      hdr: { value: DEFAULTS.hdr },
      lutStrength: { value: DEFAULTS.lutStrength },
      res: { value: new THREE.Vector2(w,h) },
      time: { value: 0.0 }
    },
    vertexShader: `#version 300 es
      in vec3 position;
      in vec2 uv;
      out vec2 vUv;
      void main(){
        vUv = uv;
        gl_Position = vec4(position, 1.0);
      }
    `,
    fragmentShader: `#version 300 es
      precision highp float;
      in vec2 vUv;
      out vec4 outColor;

      uniform sampler2D frame;
      uniform sampler2D lutTex;
      uniform vec2 res;

      uniform float smooth;
      uniform float clarity;
      uniform float detail;
      uniform float hdr;
      uniform float lutStrength;
      uniform float time;

      float luma(vec3 c){ return dot(c, vec3(0.299,0.587,0.114)); }

      vec3 blur13(vec2 uv, vec2 texel){
        vec3 c = vec3(0.0);
        c += texture(frame, uv + vec2(0.0, texel.y)).rgb * 0.15;
        c += texture(frame, uv - vec2(0.0, texel.y)).rgb * 0.15;
        c += texture(frame, uv + vec2(texel.x, 0.0)).rgb * 0.15;
        c += texture(frame, uv - vec2(texel.x, 0.0)).rgb * 0.15;
        c += texture(frame, uv).rgb * 0.40;
        return c;
      }

      void main(){
        vec2 texel = 1.0 / res;
        vec3 base = texture(frame, vUv).rgb;

        vec3 blurSkin = blur13(vUv, texel);
        float diff = abs(luma(base) - luma(blurSkin));
        float edgeW = 1.0 - smoothstep(0.02, 0.08, diff);

        vec3 smoothCol = mix(base, blurSkin, smooth * edgeW);
        vec3 sharp = smoothCol + (smoothCol - blurSkin) * clarity;
        vec3 mixed = mix(smoothCol, sharp, clarity);

        mixed += mixed * detail * 0.2;
        mixed = pow(mixed, vec3(1.0 - hdr));

        vec3 lutSample = texture(lutTex, vUv).rgb;
        mixed = mix(mixed, lutSample, lutStrength);

        outColor = vec4(clamp(mixed, 0.0, 1.0), 1.0);
      }
    `
  });

  return mat;
}

/* enable engine — starts renderer, material, returns control handle */
export async function enableSnapRemini(options = {}) {
  // options:
  //  disableFaceMask: true -> hide faceCanvas drawing
  //  enableFaceMesh: true -> uses mediapipe FaceMesh if available for portrait blur
  const { disableFaceMask = true, enableFaceMesh = true } = options;

  videoEl = document.getElementById('cam');
  gpuCanvas = document.getElementById('gpu');

  if(!videoEl || !gpuCanvas){
    console.error('enableSnapRemini: missing #cam or #gpu elements');
    throw new Error('Missing #cam or #gpu');
  }

  // wait video ready
  await new Promise(res=>{
    if(videoEl.readyState >= 2) return res();
    videoEl.onloadeddata = ()=> res();
  });

  neutralLUT = neutralLUT || makeNeutralLUT();

  // Try to create WebGL2 context; fall back to default if unavailable
  let context = null;
  try{
    context = gpuCanvas.getContext('webgl2', { antialias: true, alpha: true });
  }catch(e){}
  // if webgl2 not available, let Three create (it will fallback) — but our shader uses GLSL3; try WebGL2 first
  renderer = new THREE.WebGLRenderer({ canvas: gpuCanvas, context: context || undefined, antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  const w = videoEl.videoWidth || gpuCanvas.clientWidth || 640;
  const h = videoEl.videoHeight || gpuCanvas.clientHeight || 480;
  renderer.setSize(w, h, false);

  scene = new THREE.Scene();
  camera = new THREE.OrthographicCamera(-1,1,1,-1,0,1);

  // create VideoTexture (Three has internal safety for not-ready video)
  videoTexture = new THREE.VideoTexture(videoEl);
  videoTexture.minFilter = THREE.LinearFilter;
  videoTexture.magFilter = THREE.LinearFilter;
  videoTexture.format = THREE.RGBFormat;

  material = buildMaterial(videoTexture, w, h);
  mesh = new THREE.Mesh(new THREE.PlaneGeometry(2,2), material);
  scene.add(mesh);

  // resize handling
  window.addEventListener('resize', ()=>{
    const ww = videoEl.videoWidth || gpuCanvas.clientWidth || window.innerWidth;
    const hh = videoEl.videoHeight || gpuCanvas.clientHeight || window.innerHeight;
    renderer.setSize(ww, hh, false);
    if(material && material.uniforms && material.uniforms.res){
      material.uniforms.res.value.set(ww, hh);
    }
  });

  // Animate loop
  let prev = performance.now();
  function loop(){
    requestAnimationFrame(loop);
    const now = performance.now();
    const dt = (now - prev) / 1000; prev = now;
    if(material && material.uniforms){
      if(material.uniforms.frame && material.uniforms.frame.value) material.uniforms.frame.value.needsUpdate = true;
      if(material.uniforms.time) material.uniforms.time.value += dt;
    }
    renderer.render(scene, camera);
  }
  loop();

  // Optionally disable face overlay canvas to avoid mask
  if(disableFaceMask){
    const fc = document.getElementById('faceCanvas');
    if(fc){ fc.style.display = 'none'; fc.width = 0; fc.height = 0; }
  }

  // If mediapipe faceMesh available and requested, we set up a lightweight loop to feed landmarks to possible portrait blur functions.
  let faceMeshInstance = null;
  let latestLandmarks = null;
  if(enableFaceMesh && typeof FaceMesh !== 'undefined'){
    try{
      faceMeshInstance = new FaceMesh({ locateFile: (f)=> `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}` });
      faceMeshInstance.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
      faceMeshInstance.onResults((res)=> {
        latestLandmarks = res.multiFaceLandmarks || null;
      });
      // feed frames to mediapipe using an async loop
      (async function feed(){
        while(true){
          if(videoEl.videoWidth > 0){
            try { await faceMeshInstance.send({ image: videoEl }); } catch(e){ /* ignore frame errors */ }
          }
          await new Promise(r=>setTimeout(r, 33)); // ~30fps feeding
        }
      })();
    }catch(e){
      console.warn('FaceMesh init failed', e);
      faceMeshInstance = null;
    }
  }

  console.log('enableSnapRemini: engine started');

  // control handle
  const handle = {
    setFilter: async (name)=>{
      await applyProFilter(name);
    },
    applyLUT: async (url)=>{
      await applyLUT(url);
    },
    toggleCamera: async ()=>{
      // just reload page is simplest, but try flipping facingMode if possible
      const tracks = videoEl.srcObject?.getVideoTracks();
      if(tracks && tracks.length){
        // try to stop then restart with opposite facing mode (best-effort)
        tracks.forEach(t=>t.stop());
        // find current facingMode? fallback: reload
        location.reload();
      } else location.reload();
    },
    stop: ()=>{
      try{
        videoEl.srcObject?.getTracks().forEach(t=>t.stop());
      }catch(e){}
      try{ renderer.dispose(); }catch(e){}
    },
    _internals: { renderer, scene, camera, mesh, material, videoTexture }
  };

  // return handle so page code can call setFilter etc.
  return handle;
}

/* apply LUT (non-blocking) */
export async function applyLUT(url){
  if(!material || !material.uniforms) {
    console.warn('applyLUT: material not ready yet');
    return;
  }
  if(!url){
    material.uniforms.lutTex.value = neutralLUT || makeNeutralLUT();
    return;
  }
  const loader = new THREE.TextureLoader();
  loader.load(url, (tex)=>{
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    material.uniforms.lutTex.value = tex;
  }, undefined, (err)=>{
    console.warn('applyLUT failed', err);
    material.uniforms.lutTex.value = neutralLUT || makeNeutralLUT();
  });
}

/* apply preset filter by name */
export async function applyProFilter(name){
  if(!material || !material.uniforms) return;
  const p = PRESETS[name] || PRESETS['beauty'] || PRESETS['none'];
  material.uniforms.smooth.value = p.smooth;
  material.uniforms.clarity.value = p.clarity;
  material.uniforms.detail.value = p.detail;
  material.uniforms.hdr.value = p.hdr;
  // LUT load
  await applyLUT(p.lut);
}

export default { enableSnapRemini, applyLUT, applyProFilter };
