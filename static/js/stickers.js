document.getElementById("addStickerBtn").onclick=()=>{
    let st=document.createElement("img");
    st.src="https://via.placeholder.com/60?text=😀";
    st.className="sticker";
    st.style.top="100px"; 
    st.style.left="100px";
    stickerOverlay.appendChild(st);

    let drag=false,ox=0,oy=0;
    st.onmousedown=e=>{drag=true;ox=e.offsetX;oy=e.offsetY;}
    onmousemove=e=>{if(drag)st.style.left=e.clientX-ox+"px",st.style.top=e.clientY-oy+"px";}
    onmouseup=()=>drag=false;
};
