document.addEventListener("DOMContentLoaded", () => {

    /* ================= SAFETY ================= */
    window.onerror = function(msg, url, line){
        console.error("JS ERROR:", msg, "Line:", line);
    };

    if(typeof io === "undefined"){
        alert("Socket.IO load nahi hua, white screen ka reason!");
        throw new Error("Socket.IO missing");
    }

    /* ================= SOCKET ================= */
    const socket = io();
    const chat_id = window.chat_id;
    const me = window.me;

    socket.on("connect", () => {
        if(chat_id) socket.emit("join_chat", { chat_id });
    });

    /* ================= ELEMENTS ================= */
    const msgInput = document.getElementById("msgInput");
    const sendBtn = document.getElementById("sendBtn");
    const attachInput = document.getElementById("attachInput");
    const attachBtn = document.getElementById("attachBtn");
    const messagesArea = document.getElementById("messagesArea");
    const typingIndicator = document.getElementById("typingIndicator");
    const statusText = document.getElementById("userStatus");
    const activeDot = document.getElementById("activeDot");
    const voiceBtn = document.getElementById("voiceBtn");

    /* ================= HELPERS ================= */
    function scrollBottom(){
        if(!messagesArea) return;
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    function timeText(t){
        if(!t) return "";
        try{
            return new Date(t.replace(" ", "T"))
                .toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
        }catch{
            return "";
        }
    }

    /* ================= RENDER ================= */
    function renderMessage(m, isMine){
        if(!messagesArea || !m) return;

        const row = document.createElement("div");
        row.className = "msg-row " + (isMine ? "me" : "them");

        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";

        if(m.deleted){
            bubble.innerText = "Message deleted";
        }
        else if(m.attachment){
            if(m.attachment.startsWith("data:image")){
                const img = document.createElement("img");
                img.src = m.attachment;
                img.className = "chat-photo";
                bubble.appendChild(img);
            }
            else if(m.attachment.startsWith("data:audio")){
                const audio = document.createElement("audio");
                audio.controls = true;
                audio.src = m.attachment;
                bubble.appendChild(audio);
            }
            if(m.msg){
                const cap = document.createElement("div");
                cap.className = "caption";
                cap.innerText = m.msg;
                bubble.appendChild(cap);
            }
        }
        else{
            bubble.innerText = m.msg || "";
        }

        const meta = document.createElement("div");
        meta.className = "meta";

        const time = document.createElement("span");
        time.className = "time";
        time.innerText = timeText(m.created_at);
        meta.appendChild(time);

        if(isMine){
            const tick = document.createElement("span");
            tick.className = "tick";
            tick.innerText = m.seen ? "✔✔" : "✔";
            if(m.seen) tick.classList.add("seen");
            meta.appendChild(tick);
        }

        bubble.appendChild(meta);
        row.appendChild(bubble);
        messagesArea.appendChild(row);
        scrollBottom();
    }

    /* ================= LOAD OLD ================= */
    if(Array.isArray(window.initialMessages)){
        window.initialMessages.forEach(m=>{
            renderMessage(m, m.sender_id === me);
        });
    }

    /* ================= SEND ================= */
    let pendingAttachment = null;

    if(attachBtn && attachInput){
        attachBtn.onclick = ()=> attachInput.click();

        attachInput.onchange = e=>{
            const file = e.target.files[0];
            if(!file) return;
            const r = new FileReader();
            r.onload = ()=> pendingAttachment = r.result;
            r.readAsDataURL(file);
        };
    }

    if(sendBtn && msgInput){
        sendBtn.onclick = ()=>{
            const text = msgInput.value.trim();
            if(!text && !pendingAttachment) return;

            socket.emit("send_message", {
                chat_id,
                msg: text,
                attachment_url: pendingAttachment
            });

            msgInput.value = "";
            pendingAttachment = null;
        };

        msgInput.addEventListener("keydown", e=>{
            if(e.key === "Enter"){
                e.preventDefault();
                sendBtn.click();
            }
        });
    }

    /* ================= RECEIVE ================= */
    socket.on("new_message", d=>{
        if(!d || d.chat_id !== chat_id) return;
        renderMessage(d.message, d.message.sender_id === me);
        socket.emit("seen", { chat_id });
    });

    /* ================= SEEN ================= */
    socket.on("messages_seen", d=>{
        if(!d || d.chat_id !== chat_id) return;
        document.querySelectorAll(".msg-row.me .tick").forEach(t=>{
            t.innerText = "✔✔";
            t.classList.add("seen");
        });
    });

    /* ================= TYPING ================= */
    let typingTimer;
    if(msgInput){
        msgInput.addEventListener("input", ()=>{
            socket.emit("typing", { chat_id });
        });
    }

    socket.on("typing", d=>{
        if(!typingIndicator || d.chat_id !== chat_id) return;
        typingIndicator.classList.remove("hidden");
        clearTimeout(typingTimer);
        typingTimer = setTimeout(()=>{
            typingIndicator.classList.add("hidden");
        },1200);
    });

    /* ================= PRESENCE ================= */
    socket.on("presence", d=>{
        if(!d || d.chat_id !== chat_id) return;
        if(d.status === "online"){
            if(statusText) statusText.innerText = "Active now";
            if(activeDot) activeDot.classList.add("online");
        }else{
            if(statusText) statusText.innerText = "Offline";
            if(activeDot) activeDot.classList.remove("online");
        }
    });

    /* ================= VOICE ================= */
    let mediaRecorder, audioChunks = [];

    if(voiceBtn && navigator.mediaDevices){
        voiceBtn.onclick = async ()=>{
            try{
                if(mediaRecorder && mediaRecorder.state === "recording"){
                    mediaRecorder.stop();
                    voiceBtn.innerText = "🎤";
                    return;
                }
                const stream = await navigator.mediaDevices.getUserMedia({audio:true});
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = e=> audioChunks.push(e.data);
                mediaRecorder.onstop = ()=>{
                    const blob = new Blob(audioChunks,{type:"audio/webm"});
                    const r = new FileReader();
                    r.onload = ()=> socket.emit("send_message", {
                        chat_id,
                        attachment_url: r.result
                    });
                    r.readAsDataURL(blob);
                };

                mediaRecorder.start();
                voiceBtn.innerText = "⏹";
            }catch(err){
                console.error(err);
            }
        };
    }

    /* ================= LEAVE ================= */
    window.addEventListener("beforeunload", ()=>{
        socket.emit("leave", { chat_id });
    });

});
