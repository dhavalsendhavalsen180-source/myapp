

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

    alert("🔥 ALLY BUTTON CLICKED: " + targetId);

    const btn = document.getElementById("privateFollowBtn");

    console.log("PRIVATE BUTTON:", btn);

    if (!btn) {
        alert("❌ privateFollowBtn NOT FOUND");
        return;
    }

    if (btn.disabled) {
        alert("❌ BUTTON DISABLED");
        return;
    }

    btn.disabled = true;
    btn.innerText = "⏳ Sending...";

    try {

        console.log("📡 Sending request to:", `/social/follow/${targetId}`);

        const response = await fetch(
            `/social/follow/${targetId}`,
            {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            }
        );

        console.log("📡 STATUS:", response.status);

        const data = await response.json();

        console.log("📡 RESPONSE:", data);

        if (!response.ok || !data.ok) {

            alert(
                "❌ Error: " +
                (data.error || "Something went wrong")
            );

            btn.disabled = false;
            btn.innerText = "✨ Ally";

            return;
        }

        if (data.action === "requested") {

            alert("✅ Follow Request Sent");

            window.location.reload();

            return;
        }

        alert("⚠️ Unknown action: " + data.action);

        btn.disabled = false;
        btn.innerText = "✨ Ally";

    } catch (error) {

        console.error("REQUEST ERROR:", error);

        alert("❌ Network/JSON Error: " + error.message);

        btn.disabled = false;
        btn.innerText = "✨ Ally";
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

