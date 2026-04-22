// -----------------------------------------
// BASE CAMERA + FILTER SYSTEM
// -----------------------------------------

const video = document.getElementById("cam");
const filterList = document.getElementById("filterList");

// BASIC FILTERS LIST (Later 50+ add karenge)
let filters=[
  {name:"Normal",css:"none"},
  {name:"Bright",css:"brightness(1.2)"},
  {name:"Contrast",css:"contrast(1.3)"},
  {name:"Warm",css:"hue-rotate(20deg) saturate(1.3)"},
  {name:"Cool",css:"hue-rotate(-20deg) saturate(1.3)"},
  {name:"Smooth Skin",css:"blur(1.5px) brightness(1.1)"},
];

// UI Buttons generate karna
filters.forEach(f=>{
  let div=document.createElement("div");
  div.className="filter";
  div.innerHTML=`<img src="https://via.placeholder.com/70?text=${f.name}">`;
  div.onclick=()=>{ video.style.filter=f.css; setActive(div); };
  filterList.appendChild(div);
});
function setActive(e){
  document.querySelectorAll(".filter").forEach(x=>x.classList.remove("active"));
  e.classList.add("active");
}


// -----------------------------------------
// 🔥 SNAPCHAT FACE-MESH TRACKING LAYER
// -----------------------------------------

document.addEventListener('DOMContentLoaded',()=>{

try{

// Canvas create if not exist
if(!document.getElementById('faceCanvas')){
 const c=document.createElement('canvas');
 c.id='faceCanvas';
 c.width=1280;
 c.height=720;
 c.style.position='absolute';
 c.style.top='0';
 c.style.left='0';
 c.style.zIndex='50';
 c.style.pointerEvents='none';
 document.querySelector('.camera-area').appendChild(c);
}
window.faceCanvas=document.getElementById('faceCanvas');
window.faceCtx=faceCanvas.getContext('2d');


// MEDIAPIPE IMPORT
const faceMesh=new FaceMesh({
 locateFile:(f)=>`https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`
});

faceMesh.setOptions({
 maxNumFaces:1,
 refineLandmarks:true,
 minDetectionConfidence:0.6,
 minTrackingConfidence:0.6
});

faceMesh.onResults(res=>{
 faceCtx.clearRect(0,0,faceCanvas.width,faceCanvas.height);
 if(!res.multiFaceLandmarks) return;

 const vid=document.getElementById('cam');
 if(vid.videoWidth){
   faceCanvas.width=vid.videoWidth;
   faceCanvas.height=vid.videoHeight;
 }

 for(const lm of res.multiFaceLandmarks){
   drawConnectors(faceCtx,lm,FACEMESH_TESSELATION,{color:"#00ffea88",lineWidth:1});
   drawLandmarks(faceCtx,lm,{color:"#fff",lineWidth:0.5});
 }

});


// CAMERA -> TRACKING STREAM
navigator.mediaDevices.getUserMedia({video:true}).then(s=>{
 video.srcObject=s;

 const camFeed=new Camera(video,{
  onFrame:()=> faceMesh.send({image:video}),
  width:1280,
  height:720
 });
 camFeed.start();

});

}catch(e){console.log(e)}

});
