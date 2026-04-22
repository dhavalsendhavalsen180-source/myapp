// camera.js — handles camera preview + pick media_path and open editor
const cameraPreview = document.getElementById('cameraPreview');
const useCameraBtn = document.getElementById('useCameraBtn');
const galleryInput = document.getElementById('galleryInput');
const openEditorFromCamera = document.getElementById('openEditorFromCamera');

let cameraStream;

async function startCamera(){
  try{
    cameraStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user_id'}, audio:false});
    cameraPreview.srcObject = cameraStream;
    cameraPreview.play();
  }catch(e){
    console.warn('camera err', e);
  }
}
useCameraBtn.addEventListener('click', e => {
  startCamera();
  openEditorFromCamera.href = "#"; // will require user_id to capture or use "Edit" flow
});

// gallery -> upload selected media_path to editor upload endpoint (client side submit)
galleryInput.addEventListener('change', (e)=>{
  const f = e.target.files[0];
  if(!f) return;
  // create FormData and POST to /create/editor (server saves to editor_temp and redirects to editor work)
  const fd = new FormData();
  fd.append('media', f);
  fetch('/create/editor', { method:'POST', body: fd })
    .then(r => {
      if(r.redirected) window.location = r.url;
      else return r.text();
    })
    .catch(err => console.error(err));
});
