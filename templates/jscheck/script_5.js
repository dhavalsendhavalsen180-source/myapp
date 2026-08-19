

function openProfileMenu(){
document.getElementById("profileMenu").classList.remove("hidden");
}

document.getElementById("profileMenu").onclick=function(e){
if(e.target.id=="profileMenu"){
this.classList.add("hidden");
}
}

function openProfilePhoto(){

document.getElementById("profileMenu").classList.add("hidden");

document.getElementById("photoViewer").classList.remove("hidden");

}

document.getElementById("photoViewer").onclick=function(){

this.classList.add("hidden");

}

