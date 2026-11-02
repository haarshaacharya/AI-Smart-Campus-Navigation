
import cv2
import speech_recognition as sr
import sounddevice as sd
import serial
import time
import threading
import pythoncom
import win32com.client
import os
import socket
import qrcode

from io import BytesIO
from flask import (
    Flask, jsonify, render_template, request, Response, send_file
)

app = Flask(__name__)

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

ARDUINO_PORT = "COM3"
BAUD_RATE = 9600
CAMERA_INDEX = 0

WELCOME_SECONDS = 3
CAMERA_PREVIEW_SECONDS = 2
THANKYOU_SECONDS = 4
FACE_ABSENCE_SECONDS = 2

# --------------------------------------------------
# ARDUINO
# --------------------------------------------------

arduino = None
arduino_lock = threading.Lock()

try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    arduino.write(b"0")
    arduino.flush()
    print("Arduino connected.")

except Exception as error:
    arduino = None
    print("Arduino not connected:", error)


def update_arduino(route=None):

    if arduino is None:
        return "DISCONNECTED"

    commands = {
        "library": b"L",
        "canteen": b"A",
        "cse": b"C",
        "washroom": b"W"
    }

    try:
        command = commands.get(route, b"0")

        with arduino_lock:
            if arduino.is_open:
                arduino.write(command)
                arduino.flush()

        return "ON" if route in commands else "OFF"

    except Exception as error:
        print("Arduino error:", error)
        return "DISCONNECTED"


# --------------------------------------------------
# DESTINATIONS
# --------------------------------------------------

destinations = {
    "library": {
        "name": "Library",
        "direction": "The Library is straight ahead."
    },
    "canteen": {
        "name": "Canteen",
        "direction": "The Canteen is on your left."
    },
    "cse": {
        "name": "CSE Department",
        "direction": "The CSE Department is on your right."
    },
    "washroom": {
        "name": "Washroom",
        "direction": "The Washroom is behind you."
    }
}


# --------------------------------------------------
# GLOBAL STATE
# --------------------------------------------------

state_lock = threading.Lock()
voice_lock = threading.Lock()
conversation_lock = threading.Lock()
frame_lock = threading.Lock()

system_state = {
    "screen": "welcome",
    "status": "Welcome",
    "face_detected": False,
    "destination": None,
    "direction": "Welcome to Smart Campus",
    "active_route": None,
    "led_status": "OFF",
    "conversation": "idle",
    "message": "Welcome in Smart Campus"
}

shutdown_event = threading.Event()
session_stop_event = threading.Event()

visitor_active = False
wait_for_face_to_leave = False

camera = None
latest_frame = None
camera_ready = False

# App startup time controls the welcome and camera sequence.
app_start_time = time.time()


def set_state(**values):
    with state_lock:
        system_state.update(values)


def get_state():
    with state_lock:
        return dict(system_state)


# --------------------------------------------------
# NETWORK IP FOR MOBILE QR
# --------------------------------------------------

def get_local_ip():

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip

    except Exception:
        return "127.0.0.1"


# --------------------------------------------------
# VOICE OUTPUT
# --------------------------------------------------

def speak(message):

    print("AI:", message)

    with voice_lock:
        try:
            pythoncom.CoInitialize()

            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Rate = -1
            voice.Speak(message)

        except Exception as error:
            print("Speech output error:", error)

        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


# --------------------------------------------------
# VOICE INPUT
# --------------------------------------------------

recognizer = sr.Recognizer()


def listen():

    print("Listening...")

    try:
        recording = sd.rec(
            int(5 * 16000),
            samplerate=16000,
            channels=1,
            dtype="int16"
        )

        sd.wait()

        audio_data = sr.AudioData(
            recording.tobytes(),
            16000,
            2
        )

        text = recognizer.recognize_google(
            audio_data,
            language="en-IN"
        )

        text = text.lower().strip()

        print("Visitor:", text)

        return text

    except sr.UnknownValueError:
        return ""

    except sr.RequestError:
        speak("Internet connection is required for voice recognition.")
        return ""

    except Exception as error:
        print("Microphone error:", error)
        return ""


# --------------------------------------------------
# DESTINATION RECOGNITION
# --------------------------------------------------

def detect_destination(text):

    text = text.lower()

    if "library" in text:
        return "library"

    if "canteen" in text:
        return "canteen"

    if (
        "washroom" in text
        or "toilet" in text
        or "restroom" in text
    ):
        return "washroom"

    if (
        "cse" in text
        or "computer science" in text
        or "computer department" in text
    ):
        return "cse"

    return None


# --------------------------------------------------
# END-OF-VISIT RECOGNITION
# --------------------------------------------------

def is_finished(text):

    text = text.lower().strip()
    text = text.replace(".", "").replace(",", "")
    text = text.replace("!", "").replace("?", "")

    phrases = [
        "no",
        "no thank you",
        "no thank you sir",
        "no thanks",
        "no thanks sir",
        "that's all",
        "that is all",
        "nothing else",
        "no more",
        "thank you",
        "thank you sir",
        "no sir"
    ]

    # Exact phrase matching avoids ending a session
    # when the visitor says something like "No, Library".
    return text in phrases


# --------------------------------------------------
# RESET VISITOR STATE
# --------------------------------------------------

def reset_to_camera():

    global visitor_active, wait_for_face_to_leave

    if shutdown_event.is_set():
        return

    visitor_active = False
    wait_for_face_to_leave = True

    set_state(
        screen="camera",
        status="Waiting for visitor",
        face_detected=False,
        destination=None,
        direction="Waiting for visitor",
        active_route=None,
        led_status="OFF",
        conversation="idle",
        message="Waiting for next visitor"
    )


# --------------------------------------------------
# THANK YOU SCREEN
# --------------------------------------------------

def finish_visitor():

    update_arduino(None)

    set_state(
        screen="thankyou",
        status="Thank You",
        face_detected=False,
        destination=None,
        direction="Thank you for visiting!",
        active_route=None,
        led_status="OFF",
        conversation="idle",
        message="Thank You"
    )

    time.sleep(THANKYOU_SECONDS)

    reset_to_camera()


# --------------------------------------------------
# STOP TIMER
# --------------------------------------------------

def stop_timer():

    time.sleep(THANKYOU_SECONDS)

    if shutdown_event.is_set():
        return

    reset_to_camera()


# --------------------------------------------------
# VISITOR CONVERSATION
# --------------------------------------------------

def visitor_conversation():

    global visitor_active

    if not conversation_lock.acquire(blocking=False):
        return

    visitor_active = True
    session_stop_event.clear()

    try:

        set_state(
            screen="dashboard",
            status="Visitor detected",
            face_detected=True,
            destination=None,
            direction="Welcome to Smart Campus",
            active_route=None,
            led_status="OFF",
            conversation="active",
            message="Welcome to Smart Campus Navigation"
        )

        speak(
            "Welcome to Smart Campus Navigation. "
            "Where would you like to go, sir?"
        )

        while not shutdown_event.is_set():

            if session_stop_event.is_set():
                break

            spoken_text = listen()

            if session_stop_event.is_set():
                break

            if not spoken_text:
                speak(
                    "Sorry, I could not understand. "
                    "Please repeat your destination."
                )
                continue

            if is_finished(spoken_text):
                speak("You're welcome, sir.")

                if not session_stop_event.is_set():
                    finish_visitor()

                return

            route = detect_destination(spoken_text)

            if route:

                selected = destinations[route]

                # Turn the selected destination LEDs ON.
                # Other destination LEDs turn OFF.
                led_status = update_arduino(route)

                set_state(
                    screen="dashboard",
                    status="Navigating",
                    destination=selected["name"],
                    direction=selected["direction"],
                    active_route=route,
                    led_status=led_status,
                    conversation="active",
                    message=selected["direction"]
                )

                speak(selected["direction"])
                speak("Would you like to go anywhere else, sir?")

            else:

                speak(
                    "Please say Library, Canteen, "
                    "CSE Department, or Washroom."
                )

    except Exception as error:
        print("Conversation error:", error)

    finally:

        if session_stop_event.is_set() and not shutdown_event.is_set():
            update_arduino(None)

        visitor_active = False

        conversation_lock.release()


# --------------------------------------------------
# CAMERA AND FACE DETECTION
# --------------------------------------------------

def camera_worker():

    global camera
    global latest_frame
    global camera_ready
    global wait_for_face_to_leave

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():

        set_state(
            screen="error",
            status="Camera unavailable",
            message="Camera not found. Please check your webcam."
        )

        print("Camera not found.")
        return

    camera_ready = True

    print("Camera started.")

    no_face_start = time.time()

    while not shutdown_event.is_set():

        success, frame = camera.read()

        if not success:
            time.sleep(0.1)
            continue

        frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        for (x, y, w, h) in faces:

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 220, 80),
                2
            )

            cv2.putText(
                frame,
                "FACE DETECTED",
                (x, max(y - 12, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 220, 80),
                2
            )

        with frame_lock:
            latest_frame = frame.copy()

        current_time = time.time()

        # Welcome screen first, then camera preview.
        camera_start_time = app_start_time + WELCOME_SECONDS

        # Keep camera preview visible before starting conversation.
        face_trigger_time = (
            camera_start_time + CAMERA_PREVIEW_SECONDS
        )

        if current_time >= camera_start_time:

            if get_state()["screen"] == "welcome":
                set_state(
                    screen="camera",
                    status="Waiting for visitor",
                    message="Camera is ready. Waiting for visitor."
                )

        if len(faces) > 0:

            no_face_start = current_time

            if current_time >= camera_start_time:
                set_state(face_detected=True)

            # Do not open dashboard until welcome and camera preview
            # have both completed.
            if (
                current_time >= face_trigger_time
                and not visitor_active
                and not wait_for_face_to_leave
                and not shutdown_event.is_set()
            ):

                threading.Thread(
                    target=visitor_conversation,
                    daemon=True
                ).start()

        else:

            if current_time - no_face_start >= FACE_ABSENCE_SECONDS:

                wait_for_face_to_leave = False

                if not visitor_active:
                    set_state(face_detected=False)

        time.sleep(0.03)

    if camera is not None:
        camera.release()

    camera_ready = False

    print("Camera stopped.")


# --------------------------------------------------
# CAMERA STREAM
# --------------------------------------------------

def generate_frames():

    while not shutdown_event.is_set():

        with frame_lock:
            frame = (
                latest_frame.copy()
                if latest_frame is not None
                else None
            )

        if frame is None:
            time.sleep(0.1)
            continue

        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )


# --------------------------------------------------
# WEB ROUTES
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# Existing mobile UI is preserved.
@app.route("/mobile")
def mobile():
    return render_template("mobile.html")


# QR code opens the mobile page using the computer's
# local network IP, so a phone on the same Wi-Fi can scan it.
@app.route("/qr")
def qr_code():

    mobile_url = "http://" + get_local_ip() + ":5000/mobile"

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(mobile_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return send_file(
        image_buffer,
        mimetype="image/png"
    )


@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/status")
def api_status():
    return jsonify(get_state())


# --------------------------------------------------
# MANUAL NAVIGATION API
# --------------------------------------------------

@app.route("/api/navigate", methods=["POST"])
def api_navigate():

    data = request.get_json(silent=True) or {}

    route = data.get("destination")

    if route not in destinations:

        return jsonify({
            "success": False,
            "error": "Invalid destination"
        }), 400

    # Do not allow navigation before face detection.
    if get_state()["screen"] != "dashboard":

        return jsonify({
            "success": False,
            "error": "Please wait for face detection."
        }), 403

    selected = destinations[route]

    led_status = update_arduino(route)

    set_state(
        screen="dashboard",
        status="Navigating",
        destination=selected["name"],
        direction=selected["direction"],
        active_route=route,
        led_status=led_status,
        message=selected["direction"]
    )

    threading.Thread(
        target=speak,
        args=(selected["direction"],),
        daemon=True
    ).start()

    return jsonify({
        "success": True,
        **get_state()
    })


# --------------------------------------------------
# STOP NAVIGATION API
# --------------------------------------------------

@app.route("/api/stop", methods=["POST"])
def api_stop():

    session_stop_event.set()

    update_arduino(None)

    set_state(
        screen="thankyou",
        status="Thank You",
        face_detected=False,
        destination=None,
        direction="Thank you for visiting!",
        active_route=None,
        led_status="OFF",
        conversation="idle",
        message="Thank You"
    )

    threading.Thread(
        target=stop_timer,
        daemon=True
    ).start()

    return jsonify({
        "success": True,
        **get_state()
    })


# --------------------------------------------------
# EXIT APPLICATION API
# --------------------------------------------------

@app.route("/api/exit", methods=["POST"])
def api_exit():

    shutdown_event.set()
    session_stop_event.set()

    update_arduino(None)

    # H key closes the Python application.
    threading.Timer(
        1,
        lambda: os._exit(0)
    ).start()

    return jsonify({"success": True})


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":

    threading.Thread(
        target=camera_worker,
        daemon=True
    ).start()

    print("--------------------------------------")
    print("AI SMART CAMPUS NAVIGATION")
    print("Open: http://127.0.0.1:5000")
    print("Mobile URL: http://" + get_local_ip() + ":5000/mobile")
    print("--------------------------------------")

    try:

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )

    finally:

        shutdown_event.set()
        session_stop_event.set()

        update_arduino(None)

        if camera is not None:
            camera.release()

        if arduino is not None:

            try:
                arduino.close()
            except Exception:
                pass
