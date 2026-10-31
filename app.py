
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Initial dashboard state
system_state = {
    "status": "Ready",
    "face_detected": False,
    "destination": None,
    "direction": "Waiting for visitor",
    "active_route": None,
    "message": "Welcome to AI Smart Campus Navigation"
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify(system_state)

if __name__ == "__main__":
    print("=" * 45)
    print("AI SMART CAMPUS WEB DASHBOARD")
    print("Open: http://127.0.0.1:5000")
    print("=" * 45)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
