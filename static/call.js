const socket = window.socket || io();

let pc = null;
let localStream = null;
let chatId = window.CALL_CHAT_ID;
let callType = window.CALL_TYPE;   // null on receiver page by default

const ice = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };

const ring = new Audio("/static/sounds/inschat.mp3");
ring.loop = true;

const overlay = document.getElementById("callOverlay");
const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");
const acceptBtn  = document.getElementById("acceptCall");
const endBtn     = document.getElementById("endCall");

// ---------- HELPERS ----------
function reset() {
  ring.pause();
  if (pc) pc.close();
  pc = null;

  if (localStream) {
    localStream.getTracks().forEach(t => t.stop());
    localStream = null;
  }
}

function createPeer() {
  pc = new RTCPeerConnection(ice);

  pc.ontrack = e => remoteVideo.srcObject = e.streams[0];

  pc.onicecandidate = e => {
    if (e.candidate)
      socket.emit("webrtc_ice", { chat_id: chatId, candidate: e.candidate });
  };

  pc.onconnectionstatechange = () => {
    if (["failed","disconnected","closed"].includes(pc.connectionState))
      endCall();
  };
}

// ---------- OUTGOING CALL ----------
async function startOutgoing() {
  try {
    localStream = await navigator.mediaDevices.getUserMedia({
      audio:true,
      video: callType === "video"
    });
  } catch {
    alert("Mic / Camera permission required");
    return;
  }

  createPeer();
  localVideo.srcObject = localStream;
  localStream.getTracks().forEach(t => pc.addTrack(t, localStream));

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  // tell backend → call ringing
  socket.emit("call_request", { chat_id: chatId, type: callType });

  // send webrtc offer
  socket.emit("webrtc_offer", { chat_id: chatId, offer, type: callType });
}

// ---------- ACCEPT INCOMING ----------
acceptBtn.onclick = async () => {
  ring.pause();

  localStream = await navigator.mediaDevices.getUserMedia({
    audio:true,
    video: callType === "video"
  });

  createPeer();
  localVideo.srcObject = localStream;
  localStream.getTracks().forEach(t => pc.addTrack(t, localStream));

  socket.emit("call_accept", { chat_id: chatId });
};

// ---------- END ----------
function endCall() {
  socket.emit("call_ended", { chat_id: chatId });
  reset();
  window.location.href = `/messages/chat/${chatId}`;
}
endBtn.onclick = endCall;

// ---------- JOIN ROOM ----------
socket.emit("join", { chat_id: chatId });

// ---------- SOCKET EVENTS ----------

// incoming ringing event (receiver side)
socket.on("incoming_call", d => {
  if (d.chat_id !== chatId) return;

  callType = d.type;

  overlay.style.display = "flex";   // show popup
  ring.play().catch(()=>{});
});

// caller side — stop ring after accept
socket.on("call_accepted", () => ring.pause());

// offer received (receiver creates answer)
socket.on("webrtc_offer", async d => {
  if (!pc) createPeer();
  await pc.setRemoteDescription(d.offer);

  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);

  socket.emit("webrtc_answer", { chat_id: chatId, answer });
});

// caller receives answer
socket.on("webrtc_answer", d =>
  pc && pc.setRemoteDescription(d.answer)
);

// ICE exchange
socket.on("webrtc_ice", d =>
  pc && d.candidate && pc.addIceCandidate(d.candidate)
);

// ---------- AUTO-START ONLY IF CALLER ----------
if (window.IS_CALLER) {
    startOutgoing();
}
