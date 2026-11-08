(function () {
    "use strict";

    if (window.InsChatTabs) return;

    const tabs = {
        feed: "/posts/feed",
        explore: "/explore/",
        reels: "/reels/",
        profile: "/profile/"
    };

    let activeTab = null;

    function getTab(url) {
        const path = new URL(url, location.origin).pathname;

        if (path === "/posts/feed") return "feed";
        if (path === "/explore" || path === "/explore/") return "explore";
        if (path === "/reels" || path === "/reels/") return "reels";
        if (path.startsWith("/profile/")) return "profile";

        return null;
    }

    function saveScroll(tab) {
        if (!tab) return;

        try {
            sessionStorage.setItem(
                "inschat_scroll_" + tab,
                String(window.scrollY)
            );
        } catch (error) {
            console.warn("InsChat scroll save error:", error);
        }
    }

    function restoreScroll(tab) {
        if (!tab) return;

        try {
            const requestedTab = sessionStorage.getItem(
                "inschat_restore_tab"
            );

            if (requestedTab !== tab) return;

            const savedPosition = sessionStorage.getItem(
                "inschat_scroll_" + tab
            );

            sessionStorage.removeItem("inschat_restore_tab");

            if (savedPosition !== null) {
                const position = Number(savedPosition);

                requestAnimationFrame(function () {
                    window.scrollTo(0, position);
                });
            }
        } catch (error) {
            console.warn("InsChat scroll restore error:", error);
        }
    }

    function setActive(tab) {
        if (!tabs[tab]) return false;

        activeTab = tab;

        document.documentElement.dataset.inschatTab = tab;

        window.dispatchEvent(
            new CustomEvent("inschat:tabchange", {
                detail: { tab: tab }
            })
        );

        return true;
    }

    function handleTabClick(event) {
        if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.ctrlKey ||
            event.metaKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        const link = event.target.closest("a.js-tab-link");

        if (!link || !link.href) return;

        const targetUrl = new URL(link.href, location.origin);

        if (targetUrl.origin !== location.origin) return;

        const targetTab = getTab(targetUrl.href);

        if (!targetTab || targetTab === activeTab) return;

        saveScroll(activeTab);

        try {
            sessionStorage.setItem(
                "inschat_restore_tab",
                targetTab
            );
        } catch (error) {
            console.warn("InsChat navigation storage error:", error);
        }

        // Native navigation ko chalne do.
        // DOM aur existing scripts replace nahi honge.
    }

    window.InsChatTabs = {
        tabs: tabs,
        getTab: getTab,
        getActive: function () {
            return activeTab;
        },
        setActive: setActive,
        saveCurrentPage: function () {
            saveScroll(activeTab);
        }
    };

    activeTab = getTab(location.href);

    if (activeTab) {
        setActive(activeTab);
        restoreScroll(activeTab);
    }

    document.addEventListener("click", handleTabClick);

    window.addEventListener("pagehide", function () {
        saveScroll(activeTab);
    });

})();
