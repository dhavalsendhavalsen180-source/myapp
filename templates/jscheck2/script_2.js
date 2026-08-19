

function showTab(tab) {

    document.getElementById("posts").classList.add("hidden");
    document.getElementById("reels").classList.add("hidden");

    document.getElementById(tab).classList.remove("hidden");

    document.getElementById("tab-posts").classList.remove(
        "border-black",
        "text-black"
    );

    document.getElementById("tab-reels").classList.remove(
        "border-black",
        "text-black"
    );

    if (tab === "posts") {

        document.getElementById("tab-posts").classList.add(
            "border-b-2",
            "border-black",
            "text-black"
        );

    } else {

        document.getElementById("tab-reels").classList.add(
            "border-b-2",
            "border-black",
            "text-black"
        );
    }
}


function openEdit() {

    document.getElementById("editModal").classList.remove("hidden");
    document.getElementById("editModal").classList.add("flex");
}


function closeEdit() {

    document.getElementById("editModal").classList.add("hidden");
    document.getElementById("editModal").classList.remove("flex");
}


async function toggleFollow(targetId) {

    const btn = document.getElementById("followBtn");

    if (!btn || btn.disabled) return;

    btn.disabled = true;

    const oldText = btn.innerText.trim();

    btn.innerText = "⏳ Please wait...";

    try {

        const response = await fetch(
            `/social/follow/${targetId}`,
            {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            }
        );

        const data = await response.json();

        console.log("FOLLOW RESPONSE:", data);

        if (!response.ok || !data.ok) {

            btn.innerText = oldText;

            return;
        }


        if (data.action === "followed") {

            btn.innerText = "🤝 Allied ✓";

            btn.classList.remove(
                "ally-requested",
                "from-cyan-500",
                "via-blue-500",
                "from-amber-400",
                "via-orange-500"
            );

            btn.classList.add(
                "allied",
                "ally-success"
            );

            setTimeout(() => {

                btn.classList.remove("ally-success");

            }, 500);
        }


        else if (data.action === "unfollowed") {

            btn.innerText = "✨ Ally";

            btn.classList.remove(
                "allied",
                "ally-requested",
                "ally-success",
                "from-amber-400",
                "via-orange-500"
            );

            btn.classList.add(
                "bg-gradient-to-r",
                "from-cyan-500",
                "via-blue-500",
                "to-purple-600"
            );
        }

        else {

            btn.innerText = oldText;
        }

    } catch (error) {

        console.error("FOLLOW ERROR:", error);

        btn.innerText = oldText;

    } finally {

        btn.disabled = false;
    }
}


async function sendFollowRequest(targetId) {

    alert("FUNCTION START: " + targetId);

    const btn = document.getElementById("privateFollowBtn");

    if (!btn) {
        alert("BUTTON NOT FOUND");
        return;
    }

    if (btn.disabled) {
        alert("BUTTON ALREADY DISABLED");
        return;
    }

    btn.disabled = true;

    const oldText = btn.innerText;

    btn.innerText = "⏳ Sending...";

    try {

        alert("FETCH START");

        const response = await fetch(
            `/social/follow/${targetId}`,
            {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            }
        );

        alert("STATUS: " + response.status);

        const text = await response.text();

        alert("SERVER RESPONSE: " + text);

        let data;

        try {
            data = JSON.parse(text);
        } catch (e) {
            alert("JSON ERROR - Server JSON nahi bhej raha");
            btn.innerText = oldText;
            return;
        }

        if (!response.ok || !data.ok) {

            alert("ERROR: " + (data.error || "Unknown error"));

            btn.innerText = oldText;

            return;
        }

        if (data.action === "requested") {

            alert("REQUEST SENT SUCCESS");

            window.location.reload();

            return;
        }

        alert("UNKNOWN ACTION: " + data.action);

        btn.innerText = oldText;

    } catch (error) {

        console.error("REQUEST ERROR:", error);

        alert("FETCH ERROR: " + error.message);

        btn.innerText = oldText;

    } finally {

        btn.disabled = false;
    }
}

async function cancelFollowRequest(targetId) {

    const btn = document.getElementById("privateRequestBtn");

    if (!btn || btn.disabled) return;

    btn.disabled = true;

    const oldText = btn.innerText;

    btn.innerText = "⏳ Cancelling...";

    try {

        const response = await fetch(
            `/social/follow/${targetId}`,
            {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            }
        );

        const data = await response.json();

        console.log("CANCEL RESPONSE:", data);

        if (!response.ok || !data.ok) {

            btn.innerText = oldText;

            return;
        }

        if (data.action === "cancelled") {

            window.location.reload();

        } else {

            btn.innerText = oldText;
        }

    } catch (error) {

        console.error("CANCEL ERROR:", error);

        btn.innerText = oldText;

    } finally {

        btn.disabled = false;
    }
}


function openMenu() {

    document.getElementById("menuModal").classList.remove("hidden");
    document.getElementById("menuModal").classList.add("flex");
}


function closeMenu() {

    document.getElementById("menuModal").classList.add("hidden");
    document.getElementById("menuModal").classList.remove("flex");
}

