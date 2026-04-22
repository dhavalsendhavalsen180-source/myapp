startRecord.onclick = ()=>{
    recorder.start();
    startRecord.disabled=true;
    stopRecord.disabled=false;
}

stopRecord.onclick = ()=>{
    recorder.stop();
    startRecord.disabled=false;
    stopRecord.disabled=true;
}
