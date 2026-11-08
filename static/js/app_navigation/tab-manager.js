
(function () {
    "use strict";

    if (window.InsChatTabsManagerLoaded) return;
    window.InsChatTabsManagerLoaded = true;

    const tabRoutes = {
        feed: "/posts/feed",
        explore: "/explore",
        reels: "/reels/",
        profile: "/profile/"
    };

    function getTab(url) {
        const path = new URL(url, window.location.origin).pathname;

        if (path === "/posts/feed") return "feed";
        if (path === "/explore" || path === "/explore/") return "explore";
        if (path === "/reels" || path === "/reels/") return "reels";
        if (path.startsWith("/profile/")) return "profile";

        return null;
    }

    function switchParentTab(tab) {
        if (!tabRoutes[tab]) return false;
        if (window.parent === window) return false;

        try {
            const parentTabs = window.parent.InsChatTabs;

            if (!parentTabs ||
                typeof parentTabs.switchTab !== "function") {
                return false;
            }

            parentTabs.switchTab(tab);
            return true;

        } catch (error) {
            console.error("InsChat tab switch failed:", error);
            return false;
        }
    }

    function handleTabClick(event) {
        if (
            event.button !== 0 ||
            event.ctrlKey ||
            event.metaKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        const target = event.target;

        if (!target || typeof target.closest !== "function") return;

        const link = target.closest("a.js-tab-link");

        if (!link || !link.href) return;
        if (link.target && link.target !== "_self") return;

        const targetUrl = new URL(link.href, window.location.href);

        if (targetUrl.origin !== window.location.origin) return;

        const targetTab = getTab(targetUrl.href);

        if (!targetTab) return;
        if (window.parent === window) return;

        event.preventDefault();
        event.stopPropagation();

        switchParentTab(targetTab);
    }

    document.addEventListener("click", handleTabClick, true);

    window.InsChatTabsManager = {
        getTab: getTab,
        switchTab: switchParentTab
    };

    console.log("InsChat Tab Manager Loaded");
})();
