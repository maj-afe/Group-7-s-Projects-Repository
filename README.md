# BUG - Hands-Free Browsing Assistant

*Shared Repository for Final Year project development and documentation.*

BUG is an accessible, hands-free browsing assistant designed to let users control their computer using facial movements and voice commands. It features a modern desktop UI built with PySide6 that seamlessly connects computer vision and speech recognition pipelines.

## 🚀 Features
- **Face-Tracking Mouse Control**: Uses your webcam and Google's MediaPipe Face Landmarker to track your nose bridge and translate it into smooth cursor movements.
- **Mouth-Click System**: Automatically triggers left-clicks when you open your mouth.
- **Offline Voice Recognition**: Integrated with Vosk KaldiRecognizer for fully offline, private speech recognition.
  - *Current Status*: The voice pipeline actively listens and transcribes spoken English into text in real-time, displaying it on the dashboard.
  - *Next Steps*: Map specific phrases (e.g., "scroll down", "open browser") to PyAutoGUI OS actions.
- **Modern Dashboard UI**: A sleek, dark-mode PySide6 interface designed specifically for accessibility. It provides massive, high-contrast buttons and a minimalist layout to prevent distraction.

## 💻 OS Compatibility
- **Windows 10/11**: Fully supported out of the box.
- **Linux (Ubuntu, Arch, etc.)**: 
  - **X11 Sessions**: Fully supported.
  - **Wayland Sessions**: The camera, UI, and voice will work, but the mouse control (`pyautogui`) will fail due to Wayland's security model. You must use an X11 session or run the experimental Wayland scripts found in the `app/camera/` directory.

## 🛠️ Setup & Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/maj-afe/Group-7-s-Projects-Repository.git
   cd Group-7-s-Projects-Repository
   ```

2. **Create a Virtual Environment (Recommended)**
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On Mac/Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Core dependencies include `PySide6`, `opencv-python`, `mediapipe`, `vosk`, `sounddevice`, and `pyautogui`)*

## 🏃 Running the Application
To launch the BUG dashboard, simply run the main entry point:
```bash
python app/main.py
```
From the dashboard, you can click **"Start All Systems"** to activate the camera and voice pipelines!
