
from flask import Flask, jsonify, render_template, request, send_file
import serial
import time
import threading
import pythoncom
import win32com.client
import qrcode
import io
import socket

app = Flask(__name__)


def get_local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


LOCAL_IP = get_local_ip()
MOBILE_URL = f"http://{LOCAL_IP}:5000/mobile"


# Arduino connection
try:
    arduino = serial.Serial("COM3", 9600, timeout=1)
    time.sleep(2)

    # Starting mein all LEDs OFF
    arduino.write(b"0")
    arduino.flush()

    print("Arduino connected successfully!")

except serial.SerialException as error:
    arduino = None
    print("Arduino connection failed:", error)


system_state = {
    "status": "Ready",
    "face_detected": False,
    "destination": None,
    "direction": "Waiting for visitor",
    "active_route": None,
    "message": "Welcome to AI Smart Campus Navigation",
    "led_status": "OFF"
}


destinations = {
    "library": {
        "name": "Library",
        "direction": "You selected Library. The Library is straight ahead."
    },
    "canteen": {
        "name": "Canteen",
        "direction": "You selected Canteen. The Canteen is on your left."
    },
    "cse": {
        "name": "CSE Department",
        "direction": "You selected CSE Department. It is on your right."
    },
    "washroom": {
        "name": "Washroom",
        "direction": "You selected Washroom. It is behind you."
    }
}


voice_lock = threading.Lock()
arduino_lock = threading.Lock()
state_lock = threading.Lock()


def speak(message):
    with voice_lock:
        pythoncom.CoInitialize()
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Rate = -1
            voice.Speak(message)
        except Exception as error:
            print("Voice error:", error)
        finally:
            pythoncom.CoUninitialize()


# Arduino LED control for all four locations
def update_arduino(route):

    commands = {
        "library": b"L",
        "cse": b"C",
        "washroom": b"W",
        "canteen": b"A"
    }

    if arduino is None:
        return "DISCONNECTED"

    try:
        with arduino_lock:

            if not arduino.is_open:
                return "DISCONNECTED"

            if route in commands:
                arduino.write(commands[route])
                arduino.flush()

                print(f"{route.upper()} LEDs ON")
                return "ON"

            else:
                arduino.write(b"0")
                arduino.flush()

                print("All LEDs OFF")
                return "OFF"

    except serial.SerialException as error:
        print("Arduino error:", error)
        return "DISCONNECTED"


@app.route("/")
def home():
    return render_template(
        "index.html",
        mobile_url=MOBILE_URL
    )


@app.route("/mobile")
def mobile():
    return render_template("mobile.html")


@app.route("/qr")
def qr():
    image = qrcode.make(MOBILE_URL)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="image/png",
        max_age=0
    )


@app.route("/api/status")
def status():
    with state_lock:
        return jsonify(dict(system_state))


@app.route("/api/navigate", methods=["POST"])
def navigate():
    data = request.get_json(silent=True) or {}
    route = data.get("destination")

    if route not in destinations:
        return jsonify({
            "success": False,
            "error": "Invalid destination"
        }), 400

    destination = destinations[route]

    led_status = update_arduino(route)

    with state_lock:
        system_state["status"] = "Navigating"
        system_state["destination"] = destination["name"]
        system_state["direction"] = destination["direction"]
        system_state["active_route"] = route
        system_state["message"] = destination["direction"]
        system_state["led_status"] = led_status

        result = dict(system_state)

    threading.Thread(
        target=speak,
        args=(destination["direction"],),
        daemon=True
    ).start()

    print("Selected destination:", destination["name"])
    print("LED status:", led_status)

    return jsonify({
        "success": True,
        **result
    })


@app.route("/api/stop", methods=["POST"])
def stop():
    led_status = update_arduino(None)

    with state_lock:
        system_state.update({
            "status": "Ready",
            "destination": None,
            "direction": "Waiting for visitor",
            "active_route": None,
            "message": "Navigation stopped",
            "led_status": led_status
        })

        result = dict(system_state)

    return jsonify({
        "success": True,
        **result
    })


if __name__ == "__main__":
    print("=" * 50)
    print("AI SMART CAMPUS NAVIGATION")
    print("Laptop Dashboard: http://127.0.0.1:5000")
    print("Mobile Navigation:", MOBILE_URL)
    print("=" * 50)

    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True
        )

    finally:
        if arduino is not None:
            try:
                with arduino_lock:
                    arduino.write(b"0")
                    arduino.close()
            except serial.SerialException:
                pass
