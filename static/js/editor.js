// editor.js
const previewVideo = document.getElementById('previewVideo');
const editorVideo = document.getElementById('editorVideo');
const filterList = document.getElementById('filterList');
const brightness = document.getElementById('brightness');
const contrast = document.getElementById('contrast');
const saturation = document.getElementById('saturation');
const speed = document.getElementById('speed');
const addSticker = document.getElementById('addSticker');
const addText = document.getElementById('addText');
const musicInput = document.getElementById('musicInput');
const layersList = document.getElementById('layersList');
const trimStartBtn = document.getElementById('trimStart');
const trimEndBtn = document.getElementById('trimEnd');
const trimInfo = document.getElementById('trimInfo');
const exportVideoBtn = document.getElementById('exportVideoBtn');

let layers = []; // {type:'sticker'|'text'|'music', id, meta}
let currentFile = EDIT_FILE || '';
let trim = {start:0, end:0};

// prefill filter thumbnails
const FILTERS = [
  {name:'Normal', css:'none'},
  {name:'Warm', css:'sepia(0.25) saturate(1.2)'},
  {name:'Mono', css:'grayscale(1)'},
  {name:'Vivid', css:'saturate(1.6) contrast(1.08)'},
  {name:'Cool', css:'hue-rotate(200deg) saturate(1.1)'}
];
FILTERS.forEach(f=>{
  const img = document.createElement('div');
  img.className = 'filter-thumb';
  img.style.width='72px';
  img.style.height='72px';
  img.style.background='#222';
  img.style.display='flex';
  img.style.alignItems='center';
  img.style.justifyContent='center';
  img.style.fontSize='12px';
  img.style.color='white';
  img.style.borderRadius='8px';
  img.style.cursor='pointer';
  img.innerText = f.name;
  img.dataset.css = f.css;
  img.addEventListener('click', ()=> {
    previewVideo.style.filter = f.css;
  });
  filterList.appendChild(img);
});

// load media_path (if server passed media_path param, then video src should be /static/editor_temp/<media_path>)
if(currentFile && currentFile.length>0){
  const url = `/static/editor_temp/${currentFile}`;
  previewVideo.src = url;
  editorVideo.src = url;
  previewVideo.play().catch(()=>{});
}

// adjustments
function applyAdjust(){
  const b = brightness.value/100;
  const c = contrast.value/100;
  const s = saturation.value/100;
  previewVideo.style.filter = `brightness(${b}) contrast(${c}) saturate(${s})`;
}
brightness.addEventListener('input', applyAdjust);
contrast.addEventListener('input', applyAdjust);
saturation.addEventListener('input', applyAdjust);

// speed
speed.addEventListener('change', ()=> {
  const v = parseFloat(speed.value);
  previewVideo.playbackRate = v;
  editorVideo.playbackRate = v;
});

// stickers & text
const stickersLayer = document.getElementById('stickersLayer');
addSticker.addEventListener('click', ()=>{
  const st = document.createElement('img');
  st.src = 'https://via.placeholder.com/80?text=😀';
  st.style.position='absolute';
  st.style.top='20px'; st.style.left='20px';
  st.style.width='80px';
  st.style.cursor='move';
  st.draggable = false;
  stickersLayer.appendChild(st);
  // enable dragging
  let dragging=false, ox=0, oy=0;
  st.addEventListener('mousedown', e=>{ dragging=true; ox=e.offsetX; oy=e.offsetY; st.style.pointerEvents='auto'; });
  window.addEventListener('mousemove', e=>{ if(dragging){ st.style.left = (e.clientX-ox - stickersLayer.getBoundingClientRect().left) + 'px'; st.style.top = (e.clientY-oy - stickersLayer.getBoundingClientRect().top) + 'px'; } });
  window.addEventListener('mouseup', ()=> dragging=false);
  layers.push({type:'sticker', el:st});
  refreshLayersList();
});

addText.addEventListener('click', ()=>{
  const t = document.createElement('div');
  t.contentEditable = true;
  t.innerText = 'Edit text';
  t.style.position='absolute'; t.style.top='120px'; t.style.left='60px';
  t.style.color='white'; t.style.fontSize='24px'; t.style.textShadow='1px 1px 3px rgba(0,0,0,0.8)';
  stickersLayer.appendChild(t);
  layers.push({type:'text', el:t});
  refreshLayersList();
});

musicInput.addEventListener('change', e=>{
  const f = e.target.files[0];
  if(!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    const audioUrl = reader.result;
    const audio = new Audio(audioUrl);
    audio.loop = false;
    layers.push({type:'music', meta:{url:audioUrl, name:f.name}});
    refreshLayersList();
  };
  reader.readAsDataURL(f);
});

function refreshLayersList(){
  layersList.innerHTML = '';
  layers.forEach((L, idx)=>{
    const row = document.createElement('div');
    row.className = 'flex items-center justify-between p-1 border rounded';
    row.innerHTML = `<div class="text-sm">${idx+1}. ${L.type}</div><div><button data-idx="${idx}" class="btn-small remove-layer">Remove</button></div>`;
    layersList.appendChild(row);
  });
  document.querySelectorAll('.remove-layer').forEach(b=>{
    b.onclick = (ev) => {
      const i = parseInt(ev.target.dataset.idx);
      const item = layers[i];
      if(item.el) item.el.remove();
      layers.splice(i,1);
      refreshLayersList();
    };
  });
}

// trim helpers (simple)
let startSet=false;
trimStartBtn.addEventListener('click', ()=>{
  trim.start = previewVideo.currentTime;
  startSet=true;
  trimInfo.innerText = `Start: ${trim.start.toFixed(2)}s`;
});
trimEndBtn.addEventListener('click', ()=>{
  if(!startSet) { alert('First set start'); return; }
  trim.end = previewVideo.currentTime;
  trimInfo.innerText = `Start: ${trim.start.toFixed(2)}s End: ${trim.end.toFixed(2)}s`;
});

// Export -> create merged blob client-side by concatenating (limited) — we will just export current preview playback as blob using MediaRecorder
exportVideoBtn.addEventListener('click', async ()=>{
  try{
    const stream = previewVideo.captureStream() || editorVideo.captureStream();
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = e => { if(e.data && e.data.size) chunks.push(e.data); };
    rec.start();
    previewVideo.play();
    await new Promise(resolve => setTimeout(resolve, 2000 + (previewVideo.duration||3)*1000)); // record whole duration (approx)
    rec.stop();
    await new Promise(res => rec.onstop = res);
    const blob = new Blob(chunks, {type:'video/webm'});
    const url = URL.createObjectURL(blob);
    // send to publish page: create a form and POST to /create/editor -> server should save as editor_temp and redirect to /create/publish?media_path=...
    const fd = new FormData();
    fd.append('export', blob, 'exported_reel.webm');
    const res = await fetch('/create/editor?export=1', { method:'POST', body: fd });
    if(res.redirected) window.location = res.url;
    else {
      const txt = await res.text();
      alert('Export failed: ' + txt);
    }
  }catch(e){ console.error(e); alert('Export failed: '+e.message); }
});
