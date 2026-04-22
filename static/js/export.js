exportVideo.onclick=()=>{
    if(clips.length==0) return alert("Clip empty!");

    const blob=new Blob(clips,{type:"video/webm"});
    const url=URL.createObjectURL(blob);

    let a=document.createElement("a");
    a.href=url;
    a.download="reel.webm";
    a.click();
};
