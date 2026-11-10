// ================= GLOBAL CALL LISTENER =================

// Only parent app_shell should run the shared socket.
// Child iframe pages must not create duplicate connections.
if (window.parent !== window) {
    console.log("Shared call listener handled by parent");
} else if (typeof io !== "undefined") {

    if (!window.InsChatGlobalCallLoaded) {
        window.InsChatGlobalCallLoaded = true;

        window.socket = window.socket || io({
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000
        });

        const globalSocket = window.socket;

        console.log("InsChat shared call listener loaded");

        function joinGlobalUserRoom() {
            if (!globalSocket.connected) return;

            console.log("JOINING GLOBAL USER ROOM:", globalSocket.id);
            globalSocket.emit("join_user_room");
        }

        globalSocket.on("connect", joinGlobalUserRoom);

        // Socket pehle se connected ho to bhi room join kare
        if (globalSocket.connected) {
            joinGlobalUserRoom();
        }

        globalSocket.on("incoming_call", (d) => {

            console.log("INCOMING CALL RECEIVED:", d);

            if (!d || !d.chat_id) return;

            const ring = new Audio("/static/sounds/inschat.mp3");
            ring.loop = true;

            ring.play().catch((e) => {
                console.log("Ring blocked:", e);
            });

            window.location.href =
                "/call/" + d.chat_id +
                "?caller=0&type=" + encodeURIComponent(d.type || "audio");
        });
    }
}
