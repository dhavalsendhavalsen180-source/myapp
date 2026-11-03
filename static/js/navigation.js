(function () {
    document.addEventListener("click", function (event) {
        const link = event.target.closest("a.js-safe-back");

        if (!link) return;

        const fallback = link.dataset.fallback || "/";

        try {
            const previous = new URL(document.referrer);

            if (
                previous.origin === window.location.origin &&
                previous.href !== window.location.href &&
                window.history.length > 1
            ) {
                event.preventDefault();
                window.history.back();
            }
        } catch (error) {
            // Referrer unavailable: normal fallback link will work.
        }
    });
})();
