var i=0;

function startStories(data){
    show(data[i]);

    document.body.onclick = ()=>{
        i++;
        if(i<data.length) show(data[i]);
        else window.location="/";
    };

    setInterval(()=>{
        if(i<data.length-1) { i++; show(data[i]); }
        else window.location="/";
    },5000);
}

function show(s){
    document.getElementById("story-img").src="/static/stories/"+s.filename;

    fetch("/story/viewed",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({media_path:s.filename})
    });
}
