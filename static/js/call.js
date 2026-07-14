// ================= SOCKET =================
const socket = window.socket || io({
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000
});

window.socket = socket;

let pc = null;
let localStream = null;
let chatId = window.CALL_CHAT_ID;
let callType = window.CALL_TYPE;   // null on receiver page by default

console.log("CALL PAGE");
console.log("socket =", socket);
console.log("connected =", socket.connected);
console.log("chatId =", chatId);

// JOIN CALL ROOM
if (socket && chatId) {

  if (socket.connected) {
    console.log("JOIN CALL ROOM:", chatId);

    socket.emit("join_call_chat", {
      chat_id: chatId
    });

  } else {

    socket.on("connect", () => {
      console.log("SOCKET CONNECTED:", socket.id);

      socket.emit("join_call_chat", {
        chat_id: chatId
      });
    });

  }
}

const ice = {
  iceServers: [
    {
      urls: "stun:stun.l.google.com:19302"
    }
  ]
};

const ring = new Audio("/static/sounds/inschat.mp3");
ring.loop = true;

const overlay = document.getElementById("callOverlay");
const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");
const acceptBtn = document.getElementById("acceptCall");

console.log("acceptBtn =", acceptBtn);

const endBtn = document.getElementById("endCall");
const callerName = document.getElementById("callerName");
const callStatus = document.getElementById("callStatus");

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
    console.log("STATE:", pc.connectionState);
    if (pc.connectionState === "failed" || pc.connectionState === "closed") endCall();
  };
}

// ---------- OUTGOING CALL ----------
async function startOutgoing() {
  console.log("startOutgoing() called");
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
  console.log("EMITTING CALL REQUEST", chatId, callType);
  socket.emit("call_request", { chat_id: chatId, type: callType });
}
// ---------- ACCEPT INCOMING ----------
// ---------- ACCEPT INCOMING ----------
if (acceptBtn) {
  acceptBtn.onclick = () => {
    console.log("ACCEPT BUTTON CLICKED");

    ring.pause();
    overlay.style.display = "none";
    callStatus.innerText = "Connecting...";

    // Backend ko batao ki call accept ho gayi
    socket.emit("call_accept", {
      chat_id: chatId
    });

    // ❌ Yahan page reload mat karo.
    // Isi page par WebRTC offer receive hoga aur answer send hoga.
  };
}

// ---------- END ----------
function endCall() {
  socket.emit("call_ended", { chat_id: chatId });
  reset();
  window.location.href = `/messages/chat/${chatId}`;
}
endBtn.onclick = endCall;

// ---------- SOCKET EVENTS ----------

// incoming ringing event (receiver side)
socket.on("incoming_call", d => {
  alert("incoming_call: " + JSON.stringify(d));
  console.log("incoming_call =", d);
  if (Number(d.chat_id) !== Number(chatId)) return;

  callType = d.type;

  overlay.style.display = "flex";   // show popup
  ring.play().catch(()=>{});
});

socket.on("call_accepted", async (d) => {
  console.log("CALL ACCEPTED EVENT:", d);

  // Caller abhi call page par nahi hai to video page kholo
  if (!window.location.pathname.startsWith("/call/")) {
    window.location.href = `/call/${d.chat_id}?caller=1&type=${d.type}`;
    return;
  }

  ring.pause();
  callStatus.innerText = "Connected";

  // Agar peer abhi create nahi hua to create karo
  if (!pc) {
    createPeer();

    localStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: d.type === "video"
    });

    localVideo.srcObject = localStream;
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  }

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  socket.emit("webrtc_offer", {
    chat_id: chatId,
    offer: pc.localDescription,
    type: d.type
  });
});

// caller side — stop ring after accept

// offer received (receiver creates answer)
socket.on("webrtc_offer", async d => {
  if (!pc) createPeer();

  if (!localStream) {
    localStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: d.type === "video"
    });

    localVideo.srcObject = localStream;
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  }

  await pc.setRemoteDescription(new RTCSessionDescription(d.offer));

  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);

  socket.emit("webrtc_answer", {
    chat_id: chatId,
    answer: pc.localDescription
  });

  overlay.style.display = "none";
});

// caller receives answer
// caller receives answer
socket.on("webrtc_answer", async d => {
  if (!pc) return;
  await pc.setRemoteDescription(new RTCSessionDescription(d.answer));
});

// ICE exchange
socket.on("webrtc_ice", d =>
  pc && d.candidate && pc.addIceCandidate(d.candidate)
);

socket.on("connect", () => {
    console.log("Socket Connected");
    socket.emit("join_call_chat", { chat_id: chatId });
    if (window.IS_CALLER) {
        console.log("STARTING OUTGOING");
        startOutgoing();
    }
});


socket.on("call_rejected", () => {
  ring.pause();
  callStatus.innerText = "Call Rejected";
  setTimeout(endCall, 1000);
});

socket.on("call_timeout", () => {
  ring.pause();
  callStatus.innerText = "No Answer";
  setTimeout(endCall, 1000);
});

socket.on("call_busy", () => {
  ring.pause();
  callStatus.innerText = "User Busy";
  setTimeout(endCall, 1000);
});

socket.on("call_ended", () => {
  ring.pause();
  reset();
  window.location.href = `/messages/chat/${chatId}`;
});
