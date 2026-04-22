document.querySelectorAll(".filter-thumb").forEach(btn=>{
    btn.addEventListener("click",()=>{
        video.style.filter = btn.dataset.filter;
    });
});
