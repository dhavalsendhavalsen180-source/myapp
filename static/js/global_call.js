// ================= GLOBAL CALL LISTENER =================

if (typeof io !== "undefined" && window.me) {

    window.socket = window.socket || io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000
    });

    const globalSocket = window.socket;

    console.log("Global listener loaded");

    globalSocket.on("connect", () => {
        console.log("GLOBAL SOCKET:", globalSocket.id);
    });

    globalSocket.on("incoming_call", (d) => {

        console.log("INCOMING CALL RECEIVED:", d);

        if (!d) return;

        const ring = new Audio("/static/sounds/inschat.mp3");
        ring.loop = true;

        ring.play().catch((e) => {
            console.log("Ring blocked:", e);
        });

        window.location.href =
            "/call/" + d.chat_id +
            "?caller=0&type=" + d.type;
    });

}
