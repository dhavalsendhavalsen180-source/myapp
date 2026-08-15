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
window.socket = window.socket || io({
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000
});
const socket = window.socket;

const chat_id = window.chat_id;
const me = window.me;

socket.on("connect", () => {

    console.log("SOCKET CONNECTED JS:", socket.id);

    if(chat_id){
        socket.emit("join_chat", {
            chat_id: Number(chat_id)
        });
    }
});

socket.on("reconnect", () => {

    console.log("SOCKET RECONNECTED");

    if(chat_id){
        socket.emit("join_chat", {
            chat_id: Number(chat_id)
        });
    }
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

    let selectedMessageId = null;
let editingMessageId = null;

    const msgMenu = document.getElementById("msgMenu");
    const deleteMeBtn = document.getElementById("deleteMeBtn");
    const deleteAllBtn = document.getElementById("deleteAllBtn");
    const editMsgBtn = document.getElementById("editMsgBtn");
    const cancelMenuBtn = document.getElementById("cancelMenuBtn");

    /* ================= HELPERS ================= */
    function scrollBottom(){
        if(!messagesArea) return;
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    function timeText(t){
        if(!t) return "";

        try{
            const d = new Date(t.replace(" ", "T") + "Z");

            return d.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit"
            });
        }catch(e){
            return "";
        }
    }

/* ================= RENDER ================= */
function renderMessage(m, isMine){
    if(!messagesArea || !m) return;

    const row = document.createElement("div");
    row.className = "msg-row " + (isMine ? "me" : "them");
    row.dataset.id = m.id;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    /* ================= DELETED ================= */
    if(m.deleted){

        bubble.innerText = "Message deleted";

    }

    /* ================= SHARED POST ================= */
    else if(
        typeof m.msg === "string" &&
        m.msg.startsWith("__SHARED_POST__:")
    ){

        const postId = m.msg.split(":")[1];

        const card = document.createElement("div");
        card.className = "shared-post-card";

        /* ================= THUMBNAIL ================= */

        const img = document.createElement("img");

        img.className = "shared-post-thumbnail";

        // Default image while loading
        img.src = "/static/default_post.png";

        img.onerror = () => {
            img.onerror = null;
            img.src = "/static/default_reel.jpg";
        };

        card.appendChild(img);


        /* ================= TITLE ================= */

        const title = document.createElement("div");

        title.className = "shared-post-title";

        title.innerText = "Shared Post";

        card.appendChild(title);


        /* ================= SUBTITLE ================= */

        const subtitle = document.createElement("div");

        subtitle.className = "shared-post-subtitle";

        subtitle.innerText = "You shared a post";

        card.appendChild(subtitle);


        /* ================= VIEW POST ================= */

        const viewBtn = document.createElement("button");

        viewBtn.type = "button";

        viewBtn.className = "shared-post-view";

        viewBtn.innerText = "View Post";

        viewBtn.onclick = (e) => {

            e.stopPropagation();

            window.location.href = `/posts/${postId}`;

        };

        card.appendChild(viewBtn);


        /* ================= ADD CARD ================= */

        bubble.appendChild(card);


        /* ================= LOAD REAL THUMBNAIL ================= */

        fetch(`/posts/shared_post/${postId}`)

            .then(res => {

                if(!res.ok){

                    throw new Error(
                        "Thumbnail request failed: " + res.status
                    );

                }

                return res.json();

            })

            .then(data => {

                console.log(
                    "SHARED POST THUMBNAIL:",
                    postId,
                    data
                );

                if(data.ok && data.image){

                    img.src = data.image;

                }

            })

            .catch(err => {

                console.error(
                    "POST THUMBNAIL ERROR:",
                    err
                );

            });

    }

/* ================= SHARED REEL ================= */
else if(
    typeof m.msg === "string" &&
    m.msg.startsWith("__SHARED_REEL__:")
){

    const reelId = m.msg.split(":")[1];

    const card = document.createElement("div");
    card.className = "shared-post-card";

    const img = document.createElement("img");

    img.className = "shared-post-thumbnail";
    img.src = "/static/default_post.png";

    img.onerror = () => {
        img.src = "/static/default_post.png";
    };

    card.appendChild(img);

    const title = document.createElement("div");
    title.className = "shared-post-title";
    title.innerText = "Shared Reel";

    card.appendChild(title);

    const subtitle = document.createElement("div");
    subtitle.className = "shared-post-subtitle";
    subtitle.innerText = "You shared a reel";

    card.appendChild(subtitle);

    const viewBtn = document.createElement("button");

    viewBtn.type = "button";
    viewBtn.className = "shared-post-view";
    viewBtn.innerText = "View Reel";

    viewBtn.onclick = (e) => {
        e.stopPropagation();

        window.location.href = `/reels/${reelId}`;
    };

    card.appendChild(viewBtn);

    bubble.appendChild(card);

    // Load actual reel thumbnail
    fetch(`/reels/shared_reel/${reelId}`)
        .then(res => res.json())
        .then(data => {

            if(data.ok && data.image){
                img.src = data.image;
            }

        })
        .catch(err => {
            console.error("REEL THUMBNAIL ERROR:", err);
        });
}

/* ================= SHARED STORY ================= */
else if(
    typeof m.msg === "string" &&
    m.msg.startsWith("__SHARED_STORY__:")
){

    const storyId = m.msg.split(":")[1];

    const card = document.createElement("div");
    card.className = "shared-story-card";

    /* STORY PREVIEW */

    const media = document.createElement("div");
    media.className = "shared-story-media";

    const img = document.createElement("img");

    img.src = "/static/default_post.png";
    img.className = "shared-story-thumbnail";

    img.onerror = () => {
        img.onerror = null;
        img.src = "/static/default_post.png";
    };

    media.appendChild(img);

    /* OVERLAY */

    const overlay = document.createElement("div");
    overlay.className = "shared-story-overlay";

    const storyIcon = document.createElement("div");
    storyIcon.className = "shared-story-icon";
    storyIcon.innerText = "◎";

    const storyTitle = document.createElement("div");
    storyTitle.className = "shared-story-title";
    storyTitle.innerText = "Shared Story";

    overlay.appendChild(storyIcon);
    overlay.appendChild(storyTitle);

    media.appendChild(overlay);

    card.appendChild(media);

    /* TEXT */

    const subtitle = document.createElement("div");
    subtitle.className = "shared-story-subtitle";
    subtitle.innerText = "Someone shared a story with you";

    card.appendChild(subtitle);

    /* VIEW BUTTON */

    const viewBtn = document.createElement("button");

    viewBtn.type = "button";
    viewBtn.className = "shared-story-view";
    viewBtn.innerText = "View Story";

    viewBtn.onclick = (e) => {

        e.stopPropagation();

        window.location.href =
            `/stories/shared/${storyId}`;

    };

    card.appendChild(viewBtn);

    bubble.appendChild(card);

    /* LOAD STORY PREVIEW */

    fetch(`/stories/shared_story/${storyId}`)
        .then(res => {

            if(!res.ok){
                throw new Error(
                    "Story preview failed: " + res.status
                );
            }

            return res.json();

        })
        .then(data => {

            if(data.ok && data.image){

                img.src = data.image;

            }

        })
        .catch(err => {

            console.error(
                "STORY PREVIEW ERROR:",
                err
            );

        });
}

/* ================= STORY REPLY ================= */
else if(
    typeof m.msg === "string" &&
    m.msg.startsWith("__STORY_REPLY__:")
){

    const parts = m.msg.split(":");

    // Format:
    // __STORY_REPLY__:story_id:message
    const storyId = parts[1];
    const replyText = parts.slice(2).join(":");

    const card = document.createElement("div");
    card.className = "story-reply-card";

    /* STORY PREVIEW */
    const media = document.createElement("div");
    media.className = "story-reply-media";

    const img = document.createElement("img");

    img.className = "story-reply-thumbnail";
    img.src = "/static/default_post.png";

    img.onerror = () => {
        img.onerror = null;
        img.src = "/static/default_post.png";
    };

    media.appendChild(img);

    /* STORY LABEL */
    const label = document.createElement("div");

    label.className = "story-reply-label";
    label.innerText = "Story";

    media.appendChild(label);

    card.appendChild(media);

    /* REPLY TEXT */
    if(replyText){

        const text = document.createElement("div");

        text.className = "story-reply-text";
        text.innerText = replyText;

        card.appendChild(text);
    }

    /* OPEN STORY */
    card.onclick = () => {

        window.location.href =
            `/stories/shared/${storyId}`;

    };

    bubble.appendChild(card);

    /* LOAD STORY PREVIEW */
    fetch(`/stories/shared_story/${storyId}`)
        .then(res => {

            if(!res.ok){
                throw new Error("Story preview failed");
            }

            return res.json();

        })
        .then(data => {

            if(data.ok && data.image){
                img.src = data.image;
            }

        })
        .catch(err => {

            console.error(
                "STORY REPLY PREVIEW ERROR:",
                err
            );

        });
}

/* ================= ATTACHMENT ================= */

else if(m.attachment){

    const attachment = String(m.attachment);

    const lower = attachment.toLowerCase();


    /* ================= IMAGE ================= */

    if(
        lower.match(/\.(jpg|jpeg|png|gif|webp)(\?.*)?$/)
        ||
        lower.startsWith("data:image/")
    ){

        const img = document.createElement("img");

        img.src = attachment;

        img.className = "chat-photo";

        img.style.display = "block";
        img.style.maxWidth = "260px";
        img.style.width = "100%";
        img.style.height = "auto";
        img.style.borderRadius = "14px";
        img.style.objectFit = "cover";

        img.onload = () => {
            scrollBottom();
        };

        img.onerror = () => {
            console.error("IMAGE LOAD ERROR:", attachment);
        };

        bubble.appendChild(img);
    }


    /* ================= VIDEO ================= */

    else if(
        lower.match(/\.(mp4|webm|mov)(\?.*)?$/)
        ||
        lower.startsWith("data:video/")
    ){

        const video = document.createElement("video");

        video.src = attachment;

        video.className = "chat-video";

        video.controls = true;
        video.playsInline = true;
        video.preload = "metadata";

        video.style.display = "block";
        video.style.width = "260px";
        video.style.maxWidth = "100%";
        video.style.height = "auto";
        video.style.maxHeight = "360px";
        video.style.borderRadius = "14px";
        video.style.background = "#000";

        video.addEventListener(
            "loadedmetadata",
            scrollBottom
        );

        video.onerror = () => {
            console.error(
                "VIDEO LOAD ERROR:",
                video.error
            );
        };

        bubble.appendChild(video);
    }


    /* ================= AUDIO ================= */

    else if(
        lower.match(/\.(mp3|wav|ogg|m4a)(\?.*)?$/)
        ||
        lower.startsWith("data:audio/")
    ){

        const audio = document.createElement("audio");

        audio.controls = true;
        audio.preload = "metadata";

        audio.src = attachment;

        audio.style.width = "230px";
        audio.style.maxWidth = "100%";

        bubble.appendChild(audio);
    }


    /* ================= OTHER FILE ================= */

    else{

        const link = document.createElement("a");

        link.href = attachment;

        link.target = "_blank";

        link.rel = "noopener noreferrer";

        link.innerText = "📎 Open file";

        link.style.display = "inline-block";
        link.style.marginTop = "5px";

        bubble.appendChild(link);
    }


    /* ================= CAPTION ================= */

    if(m.msg){

        const cap = document.createElement("div");

        cap.className = "caption";

        cap.innerText = m.msg;

        cap.style.marginTop = "6px";

        bubble.appendChild(cap);
    }

}

/* ================= NORMAL MESSAGE ================= */
else{

    let displayText = m.msg || "";

    // Story reply ko normal message ki tarah show karo
    if(
        typeof displayText === "string" &&
        displayText.startsWith("__STORY_REPLY__:")
    ){

        const parts = displayText.split(":");

        // Format:
        // __STORY_REPLY__:story_id:text
        if(parts.length >= 3){

            displayText = parts
                .slice(2)
                .join(":");

        }

    }

    bubble.innerText = displayText;

}

    /* ================= META ================= */

    const meta = document.createElement("div");
    meta.className = "meta";

    const time = document.createElement("span");
    time.className = "time";
    time.innerText = timeText(m.created_at);

    meta.appendChild(time);

    /* ================= SEEN TICKS ================= */

    if(isMine){

        const tick = document.createElement("span");

        tick.className = "tick";

        tick.innerText = m.seen ? "✔✔" : "✔";

        if(m.seen){
            tick.classList.add("seen");
        }

        meta.appendChild(tick);
    }

    /* ================= LONG PRESS ================= */

    let pressTimer;

    bubble.addEventListener("touchstart", () => {

        selectedMessageId = m.id;

        if(isMine){

            deleteAllBtn.style.display = "block";
            editMsgBtn.style.display = "block";

        }else{

            deleteAllBtn.style.display = "none";
            editMsgBtn.style.display = "none";

        }

        pressTimer = setTimeout(() => {

            msgMenu.classList.add("show");

        }, 700);

    });

    bubble.addEventListener("touchend", () => {

        clearTimeout(pressTimer);

    });

    /* ================= APPEND ================= */

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

/* ================= SEND + REAL UPLOAD ================= */

/* ================= ATTACHMENT SELECT ================= */

if(attachBtn && attachInput){

    attachBtn.onclick = () => {
        attachInput.click();
    };

attachInput.onchange = async e => {

    const file = e.target.files[0];

    if(!file){
        console.log("ATTACHMENT: No file selected");
        return;
    }

    console.log("ATTACHMENT SELECTED:", {
        name: file.name,
        type: file.type,
        size: file.size,
        sizeMB: (file.size / 1024 / 1024).toFixed(2)
    });

    try {

        /* ================= UPLOAD ================= */

        const formData = new FormData();

        formData.append("file", file);

        const response = await fetch(
            `/messages/upload/${Number(chat_id)}`,
            {
                method: "POST",
                body: formData,
                credentials: "include"
            }
        );

        if(!response.ok){

            throw new Error(
                "Upload failed: HTTP " + response.status
            );

        }

        const result = await response.json();

        console.log("AUTO UPLOAD RESULT:", result);

        if(!result.ok || !result.url){

            throw new Error(
                result.error || "Upload failed"
            );

        }

        /* ================= DIRECT SEND ================= */

        socket.emit("send_message", {

            chat_id: Number(chat_id),

            msg: "",

            attachment_url: result.url

        });

        console.log("PHOTO SENT DIRECTLY:", result.url);

    }
    catch(err){

        console.error("AUTO UPLOAD ERROR:", err);

        alert("Photo send failed. Please try again.");

    }

    /* ================= RESET ================= */

    attachInput.value = "";

};

}   // <-- YE MISSING THA

/* ================= SEND ================= */

if(sendBtn && msgInput){

    sendBtn.onclick = async () => {

        const text = msgInput.value.trim();

        /* EDIT MESSAGE */
        if(editingMessageId){

            if(!text){
                return;
            }

            socket.emit("message_edit", {
                chat_id,
                message_id: editingMessageId,
                new_text: text
            });

            editingMessageId = null;
            msgInput.value = "";

            return;
        }


        /* NOTHING TO SEND */
        if(!text){
            return;
        }


        /* ================= SEND MESSAGE ================= */

        socket.emit("send_message", {

            chat_id: Number(chat_id),

            msg: text,

            attachment_url: null
        });


        /* ================= RESET ================= */

        msgInput.value = "";

        };

    /* ENTER = SEND */

    msgInput.addEventListener("keydown", e => {

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

    socket.on("message_edited", d => {

        if(!d || d.chat_id !== chat_id) return;

        const row = document.querySelector(
            `.msg-row[data-id="${d.message.id}"]`
        );

        if(!row) return;

        const bubble = row.querySelector(".msg-bubble");

        bubble.innerHTML = `
            ${d.message.msg}
            <div style="
                font-size:11px;
                opacity:.7;
                margin-top:3px;
            ">
                edited
            </div>
        `;
    });

    /* ================= badha mate dilet ================= */

    socket.on("message_deleted", d=>{
        if(!d || d.chat_id !== chat_id) return;

        const row = document.querySelector(
            `.msg-row[data-id="${d.message_id}"]`
        );

        if(row){
            const bubble = row.querySelector(".msg-bubble");
            bubble.innerHTML =
                '<div style="font-style:italic;color:#888;">Message deleted</div>';
        }
    });

    /* ================= maramate dilet ================= */
socket.on("deleted_for_me", d=>{

    if(!d || d.chat_id !== chat_id) return;

    const row = document.querySelector(
        `.msg-row[data-id="${d.message_id}"]`
    );

    if(row){
        row.remove();
    }
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

let mediaRecorder = null;
let audioChunks = [];
let voiceStream = null;

if(voiceBtn && navigator.mediaDevices){

    voiceBtn.onclick = async () => {

        try{

            /* STOP RECORDING */
            if(
                mediaRecorder &&
                mediaRecorder.state === "recording"
            ){

                mediaRecorder.stop();

                voiceBtn.innerText = "🎤";

                return;
            }


            /* MICROPHONE */
            voiceStream =
                await navigator.mediaDevices.getUserMedia({
                    audio: true
                });

            audioChunks = [];


            /* RECORDER */
            mediaRecorder =
                new MediaRecorder(voiceStream);


            mediaRecorder.ondataavailable = e => {

                if(e.data && e.data.size > 0){
                    audioChunks.push(e.data);
                }

            };


            /* STOP */
            mediaRecorder.onstop = async () => {

                try{

                    /* MIC BAND */
                    if(voiceStream){

                        voiceStream
                            .getTracks()
                            .forEach(track => track.stop());

                    }


                    /* AUDIO FILE */
                    const blob =
                        new Blob(
                            audioChunks,
                            {type: "audio/webm"}
                        );


                    if(!blob.size){

                        console.error(
                            "VOICE: Empty recording"
                        );

                        return;
                    }


                    /* ================= UPLOAD ================= */

                    const formData = new FormData();

                    formData.append(
                        "file",
                        blob,
                        "voice_" +
                        Date.now() +
                        ".webm"
                    );


                    const response =
                        await fetch(
                            `/messages/upload/${Number(chat_id)}`,
                            {
                                method: "POST",
                                body: formData,
                                credentials: "include"
                            }
                        );


                    if(!response.ok){

                        throw new Error(
                            "Voice upload HTTP " +
                            response.status
                        );

                    }


                    const result =
                        await response.json();


                    console.log(
                        "VOICE UPLOAD:",
                        result
                    );


                    if(!result.ok || !result.url){

                        throw new Error(
                            result.error ||
                            "Voice upload failed"
                        );

                    }


                    /* ================= SEND ================= */

                    socket.emit(
                        "send_message",
                        {
                            chat_id: Number(chat_id),
                            msg: "",
                            attachment_url: result.url
                        }
                    );


                }catch(err){

                    console.error(
                        "VOICE SEND ERROR:",
                        err
                    );

                    alert(
                        "Voice message send failed."
                    );

                }

            };


            /* START */
            mediaRecorder.start();

            voiceBtn.innerText = "⏹";

            console.log(
                "VOICE RECORDING STARTED"
            );

        }catch(err){

            console.error(
                "MIC ERROR:",
                err
            );

            alert(
                "Microphone permission required."
            );

        }

    };

}

/* ================= MESSAGE ACTIONS ================= */

/* DELETE FOR ME */
if(deleteMeBtn){

    deleteMeBtn.onclick = () => {

        if(!selectedMessageId){
            return;
        }

        socket.emit("delete_for_me", {
            chat_id: Number(chat_id),
            message_id: Number(selectedMessageId)
        });

        msgMenu.classList.remove("show");

    };

}


/* DELETE FOR EVERYONE */
if(deleteAllBtn){

    deleteAllBtn.onclick = () => {

        if(!selectedMessageId){
            return;
        }

        socket.emit("message_delete", {
            chat_id: Number(chat_id),
            message_id: Number(selectedMessageId)
        });

        msgMenu.classList.remove("show");

    };

}


/* EDIT MESSAGE */
if(editMsgBtn){

    editMsgBtn.onclick = () => {

        if(!selectedMessageId){
            return;
        }

        const row = document.querySelector(
            `.msg-row[data-id="${selectedMessageId}"]`
        );

        if(!row){
            msgMenu.classList.remove("show");
            return;
        }

        const bubble = row.querySelector(".msg-bubble");

        if(!bubble){
            return;
        }

        /*
         * Meta/time/ticks hata kar actual message text nikalo
         */
        const clone = bubble.cloneNode(true);

        const meta = clone.querySelector(".meta");

        if(meta){
            meta.remove();
        }

        const oldText = clone.innerText.trim();

        msgInput.value = oldText;

        editingMessageId = selectedMessageId;

        msgInput.focus();

        msgMenu.classList.remove("show");

    };

}


/* CANCEL MENU */
if(cancelMenuBtn){

    cancelMenuBtn.onclick = () => {

        msgMenu.classList.remove("show");

        selectedMessageId = null;

    };

}

/* ================= LEAVE ================= */
window.addEventListener("beforeunload", ()=>{
socket.emit("leave", { chat_id });
});

});
