
function closeReel(){
  const modal = document.getElementById("reelModal");
  const player = document.getElementById("reelPlayer");
  player.pause();
  player.src = "";
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}
