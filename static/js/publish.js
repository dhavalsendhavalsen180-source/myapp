// publish.js — preview media_path passed in query or hidden input
document.addEventListener('DOMContentLoaded', ()=>{
  const preview = document.getElementById('publishPreview');
  const hidden = document.getElementById('fileInputHidden');
  const f = hidden ? hidden.value : '';
  if(f){
    preview.src = `/static/editor_temp/${f}`;
  }
});
