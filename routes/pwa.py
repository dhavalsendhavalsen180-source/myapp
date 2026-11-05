import re

from flask import Blueprint, send_from_directory, current_app

pwa_bp = Blueprint("pwa", __name__)


@pwa_bp.route("/manifest.json")
def manifest():
    return send_from_directory(
        current_app.static_folder,
        "manifest.json",
        mimetype="application/manifest+json"
    )


@pwa_bp.route("/service-worker.js")
def service_worker():
    response = send_from_directory(
        current_app.static_folder,
        "service-worker.js",
        mimetype="application/javascript"
    )
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@pwa_bp.after_app_request
def add_inschat_pwa_metadata(response):

    if (
        response.status_code != 200
        or response.direct_passthrough
        or "text/html" not in response.headers.get("Content-Type", "")
    ):
        return response

    try:
        html = response.get_data(as_text=True)

        if not re.search(r"</head\s*>", html, re.I):
            return response

        additions = []

        if not re.search(r'<link[^>]+rel=["\']manifest["\']', html, re.I):
            additions.append(
                '<link rel="manifest" href="/manifest.json">'
            )

        if not re.search(r'<link[^>]+rel=["\']icon["\']', html, re.I):
            additions.append(
                '<link rel="icon" href="/static/icons/favicon.ico">'
            )

        if not re.search(r'<meta[^>]+name=["\']theme-color["\']', html, re.I):
            additions.append(
                '<meta name="theme-color" content="#000000">'
            )

        if not re.search(
            r'<script[^>]*>[\s\S]*serviceWorker\.register',
            html,
            re.I
        ):
            additions.append("""
<script>
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
        navigator.serviceWorker.register('/service-worker.js')
            .catch(function (error) {
                console.error('InsChat Service Worker:', error);
            });
    });
}
</script>
""")

        if additions:
            html = re.sub(
                r"</head\s*>",
                lambda match: (
                    "\n" + "\n".join(additions) + "\n" + match.group(0)
                ),
                html,
                count=1,
                flags=re.I
            )
            response.set_data(html)

    except Exception:
        current_app.logger.exception(
            "InsChat PWA metadata injection failed"
        )

    return response
