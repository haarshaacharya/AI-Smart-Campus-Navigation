import cv2
import speech_recognition as sr
import sounddevice as sd
import serial
import time
import win32com.client


arduino = serial.Serial("COM3", 9600, timeout=1)
time.sleep(2)


recognizer = sr.Recognizer()

# Windows voice engine - initialized only once
voice = win32com.client.Dispatch("SAPI.SpVoice")
voice.Rate = -1

def speak(message):
    print("Signboard:", message)
    voice.Speak(message)

def listen():
    print("\nSpeak now! (5 seconds)")

    audio = sd.rec(
        int(5 * 16000),
        samplerate=16000,
        channels=1,
        dtype="int16"
    )
    sd.wait()

    audio_data = sr.AudioData(
        audio.tobytes(),
        16000,
        2
    )

    try:
        question = recognizer.recognize_google(
            audio_data,
            language="en-IN"
        )
        print("You said:", question)
        return question.lower()

    except sr.UnknownValueError:
        print("Could not understand.")
        return ""

    except sr.RequestError:
        print("Internet connection required.")
        return ""


face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera not found!")
    arduino.close()
    raise SystemExit


WINDOW_NAME = "AI Smart Campus Signboard"
stop_requested = False

def mouse_callback(event, x, y, flags, userdata):
    global stop_requested

    if event == cv2.EVENT_LBUTTONDOWN:
        if 10 <= x <= 150 and 10 <= y <= 55:
            print("STOP / EXIT clicked.")
            stop_requested = True

cv2.namedWindow(WINDOW_NAME)
cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

print("================================")
print(" AI SMART CAMPUS SIGNBOARD")
print("================================")
print("Camera started.")
print("Click STOP / EXIT or press Q / ESC to exit.")

visitor_active = False
last_face_time = 0

try:
    while True:
        if stop_requested:
            break

        success, frame = camera.read()

        if not success:
            break

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
                (0, 255, 0),
                2
            )


        cv2.rectangle(
            frame,
            (10, 10),
            (150, 55),
            (0, 0, 220),
            -1
        )

        cv2.putText(
            frame,
            "STOP / EXIT",
            (20, 39),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:
            break

        if stop_requested:
            break

        
        if len(faces) > 0:
            last_face_time = time.time()

            if not visitor_active:
                visitor_active = True

                speak(
                    "Welcome to Smart Campus Navigation. "
                    "Where do you want to go?"
                )

                
                question = ""

                for attempt in range(3):
                    question = listen()

                    if question:
                        break

                    # Do not speak after final failed attempt
                    if attempt < 2:
                        speak(
                            "Sorry, please repeat your destination."
                        )

                
                if "library" in question:
                    arduino.write(b"L")
                    speak("Library is straight ahead.")

                elif "canteen" in question:
                    arduino.write(b"O")
                    speak("Canteen is on your left.")

                elif "cse" in question or "computer" in question:
                    arduino.write(b"O")
                    speak("C S E Department is on your right.")

                elif "washroom" in question or "toilet" in question:
                    arduino.write(b"O")
                    speak("Washroom is behind you.")

                elif question:
                    arduino.write(b"O")
                    speak("Sorry, location not found.")

                else:
                    speak(
                        "Sorry, I could not understand your question."
                    )


        if (
            visitor_active
            and len(faces) == 0
            and time.time() - last_face_time > 5
        ):
            visitor_active = False
            arduino.write(b"O")
            print("Ready for next visitor.")

except KeyboardInterrupt:
    print("\nProgram stopped.")

finally:
    try:
        arduino.write(b"O")
        arduino.close()
    except Exception:
        pass

    camera.release()
    cv2.destroyAllWindows()

    print("System closed successfully.")
