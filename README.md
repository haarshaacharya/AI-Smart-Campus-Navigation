# 🧭 AI Smart Campus Navigation System

### An Accessible, AI-Powered Campus Navigation & Smart Signboard

A smart navigation system that combines **Python, Flask, Voice Recognition, Face Detection, Arduino, and a Responsive Web Dashboard** to help visitors find important locations on a campus.

The project includes a central smart signboard and a QR-based personal mobile navigation website.

---

## 🎯 Project Objective

To make campus navigation more **accessible, interactive, and convenient** for students, visitors, staff, and people who may need additional guidance.

Instead of searching for directions manually, visitors can use an AI-powered signboard or scan a QR code to explore the campus map on their own phone.

## ✨ Key Features

- 🧭 **Interactive 2D Campus Map** — Displays routes to important locations.
- 🎙️ **Voice Recognition Prototype** — Recognizes spoken destination requests using Python.
- 🔊 **Voice Guidance** — Provides spoken navigation instructions.
- 👤 **Face Detection Prototype** — Detects a visitor using a camera.
- 💡 **Arduino LED Integration** — Controls the Arduino's built-in LED for the Library route.
- 💻 **Web Dashboard** — A Flask-based interface for destination selection and navigation status.
- 📱 **Responsive Mobile Navigation** — A mobile-friendly interface accessed through QR scanning.
- 👥 **Independent Multi-User Navigation** — Each phone can select its own destination without changing another visitor's route.
- 🎨 **Color-Coded Routes** — Green route highlighting with yellow digital LED indicators.

> **Development status:** Face detection and microphone-based voice recognition work in the standalone Python prototype. They are not yet integrated into the Flask dashboard. Additional physical LED routes are planned.

---

## 📍 Available Destinations

| Destination | Direction |
|---|---|
| 📚 Library | Straight ahead |
| 🍽️ Canteen | Left |
| 💻 CSE Department | Right |
| 🚻 Washroom | Behind the starting point |

These directions represent the current exhibition prototype layout.

---

## 🌍 Where Can We Use This System?

### 🏫 1. Schools and Colleges

Help new students, parents, and visitors find classrooms, libraries, laboratories, departments, and offices.

### 🏥 2. Hospitals

Guide patients and visitors toward reception areas, departments, waiting rooms, and other facilities.

### 🏢 3. Corporate Offices

Help employees and guests locate meeting rooms, departments, and reception areas.

### 🛍️ 4. Shopping Malls

Provide digital directions to stores, food courts, washrooms, and exits.

### 🚉 5. Railway Stations and Airports

Support navigation toward platforms, gates, information counters, and facilities.

### 🏛️ 6. Museums and Exhibition Centers

Help visitors find galleries, exhibition sections, information desks, and amenities.

**Main benefit:** The same navigation concept can be adapted to different buildings by changing the map, destinations, and route information.

---

## ⚙️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main application logic |
| Flask | Web server and dashboard |
| HTML, CSS, JavaScript | Responsive web interfaces |
| OpenCV | Camera-based face detection prototype |
| SpeechRecognition | Speech-to-text recognition |
| sounddevice | Microphone audio recording |
| Windows SAPI / pywin32 | Text-to-speech output |
| Arduino UNO | Physical LED control |
| PySerial | Python-to-Arduino communication |
| qrcode | Mobile navigation QR code |

---

## 🧠 How the System Works

### Laptop Smart Signboard

1. The laptop runs the Flask dashboard.
2. A destination is selected on the dashboard.
3. Python updates the selected route.
4. The 2D campus map highlights the route.
5. The system speaks the direction.
6. For the Library route, Python sends a command to the Arduino UNO to turn on its built-in LED.

### Personal Mobile Navigation

1. A visitor scans the QR code displayed on the laptop dashboard.
2. The phone opens the mobile navigation website.
3. The visitor chooses a destination.
4. The selected route is highlighted on that phone.
5. Directions appear on the phone.
6. Other visitors' phones and the laptop dashboard remain unaffected.

**Note:** Mobile navigation state is managed independently in each browser page. The mobile interface does not send route-selection commands to the Arduino.

---

## ♿ Accessibility Goals

The project aims to improve access to navigation information through:

- Spoken guidance from the smart signboard.
- Clearly labeled destination buttons.
- Color-coded route indicators.
- A personal mobile map.
- Multiple ways to access destination information.

Future versions can improve accessibility with multilingual instructions, screen-reader testing, and more detailed route guidance.

---

## 🔮 Future Improvements

- Integrate live camera face detection into the Flask dashboard.
- Integrate microphone-based voice recognition into the dashboard.
- Build and connect multiple physical LED routes.
- Add multilingual voice guidance.
- Add more campus destinations.
- Add accessible route information for wheelchair users.
- Improve navigation for larger, multi-floor buildings.
- Deploy the mobile website securely for access beyond the local network.

---

## 🏆 Project Category

**Artificial Intelligence • Internet of Things • Accessibility • Smart Campus • Web Development**

Built as an educational exhibition prototype demonstrating how AI-assisted interaction, digital navigation, and IoT hardware can work together
