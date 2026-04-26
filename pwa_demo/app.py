from flask import Flask, send_from_directory, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
