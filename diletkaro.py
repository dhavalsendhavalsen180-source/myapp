from flask import Flask, render_template, send_from_directory

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/sw.js")
def sw():
    return send_from_directory("static", "sw.js")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
