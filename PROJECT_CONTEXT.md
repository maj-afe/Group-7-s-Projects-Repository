# Project Context: BUG (Face Gesture Assistant)

## Project Overview

**BUG (Hands-Free Browsing Assistant)** is an adaptive, offline, multimodal control architecture designed to provide practical desktop interaction through combined facial gestures and voice commands. It aims to solve the challenges of existing hands-free systems by personalizing interaction parameters, arbitrating between facial and voice inputs, and preventing false activations.

**High-Level Features:**
- **Face & Head Tracking:** Translates natural head movements into cursor movements using a calibrated deadzone and smoothing (alpha filter). Maps looking up/down to scrolling, and horizontal turns to navigation. Mouth opening acts as mouse clicks.
- **Voice Recognition (Offline):** Leverages Silero VAD (Voice Activity Detection) and Faster-Whisper to transcribe and execute voice commands completely locally, preserving privacy and eliminating network latency.
- **Multimodal Intent Management:** Provides cross-modal control (e.g., using voice to toggle tracking, change scrolling parameters) and handles emergency stop/resume actions.
- **GUI Dashboard:** An interactive desktop application providing live camera feeds with facial landmarks, status indicators (Active/Paused/Listening), and setup/calibration wizards.

## Architecture & Patterns

- **Asynchronous & Multithreaded Execution:** To prevent blocking the main UI thread, heavy workloads are offloaded to dedicated `QThread` components (e.g., `CameraThread` for video processing and face tracking, `SpeechRecognitionThread` for audio capture and inference).
- **Event-Driven UI (Signals & Slots):** PySide6 is used for the application GUI. The background threads (`CameraThread`, `VoiceAssistant`) emit signals (e.g., `frame_ready`, `status_update`, `error_occurred`) which the `MainWindow` consumes to update the UI safely.
- **Offline ML Inference Architecture:** 
  - **Vision:** OpenCV grabs frames and passes them to the MediaPipe Face Landmarker.
  - **Audio:** `sounddevice` captures audio streams, Silero VAD segments the speech, and Faster-Whisper transcribes the segments into text strings.
- **Command Engine / Arbitration Layer:** The `CommandHandler` takes transcribed text, normalizes it, handles debouncing/deduplication, and maps it to system actions (like scrolling, window management, or clicking).
- **System Automation:** Actions like moving the mouse, clicking, and scrolling are handled via `pyautogui`, while system-level operations (lock, sleep, restart) use OS-level APIs (e.g., `ctypes.windll`, `subprocess`).

## Directory Structure

```text
.
├── app/                            # Main application package
│   ├── camera/                     # Vision processing and tracking
│   │   ├── face_cursor_windows_varient.py  # Main head tracking & cursor logic
│   │   └── face_landmarker.task            # MediaPipe model file
│   ├── system/                     # OS-level integrations
│   │   ├── system_controller.py            # OS power/lock management
│   │   ├── window_manager.py               # OS window manipulation
│   │   └── signal_bridge.py                # Thread communication signals
│   ├── ui/                         # PySide6 GUI Components
│   │   ├── main_window.py                  # Primary UI entry point and state coordinator
│   │   ├── dashboard.py                    # HUD / Control panel layout
│   │   ├── wizard_dialog.py                # Setup/calibration wizard
│   │   └── voice_overlay.py                # OSD for voice notifications
│   ├── voice/                      # Audio processing and transcription
│   │   ├── voice_assist.py                 # Main voice manager
│   │   ├── speech_recognition.py           # Thread running inference pipeline
│   │   ├── command_handler.py              # Text-to-action engine
│   │   ├── vad.py                          # Voice Activity Detection (Silero)
│   │   └── whisper_engine.py               # Offline ASR (Faster-Whisper)
│   └── main.py                     # Application Entry Point
├── tests/                          # Unit and integration tests
├── .venv/                          # Python virtual environment (ignored by Git)
├── README.md                       # Project documentation
├── RESEARCH_ROADMAP.md             # Development priorities and roadmap
├── requirements.txt                # Pip dependency list
└── run.ps1                         # PowerShell script to launch the app
```

*(Note: There is a `Group-7-s-Projects-Repository/` subdirectory in the root containing an identical file tree, which is a legacy backup/clone artifact).*

## Dependencies & Stack

- **UI Framework:** PySide6 (Qt for Python).
- **Vision/Tracking:** `opencv-python`, `mediapipe` (for fast on-device face landmarker).
- **Voice/Audio:** `sounddevice`, `pywebrtc-audio`, `silero-vad` (segmentation), `faster-whisper` (transcription).
- **System Automation:** `PyAutoGUI` (mouse/keyboard automation), `pywin32` (Windows API wrappers), `ctypes` (native Windows DLLs).
- **Utility:** `rapidfuzz` (fuzzy matching for commands), `python-dotenv`, `psutil`.
- **Testing:** `pytest`.

## Setup & Workflows

**1. Environment Setup:**
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

**2. Running the Application:**
The preferred way to run the application on Windows is via the provided PowerShell script which ensures the virtual environment is used:
```powershell
.\run.ps1
```
Alternatively, run directly via Python:
```bash
python app/main.py
```

**3. Testing:**
Run the test suite using pytest:
```bash
pytest tests/
```

**4. Building:**
A standalone executable can be built using PyInstaller (as noted in the project roadmap), wrapped inside `build.ps1` or similar scripts.

## Key Components & Entry Points

- **Entry Point (`app/main.py`):** Instantiates the Qt `QApplication`, configures defaults, and loads the `MainWindow`.
- **Application Controller (`app/ui/main_window.py`):** Central coordinator. Manages the instantiation and lifecycle of the `CameraThread` and `VoiceAssistant`, mapping their signals to the `Dashboard` UI updates.
- **Head Tracking Core (`app/camera/face_cursor_windows_varient.py`):** Contains `CameraThread`. It initializes the OpenCV capture and MediaPipe landmarker. It calculates relative distances (dx, dy) from a calibrated center anchor, applies a deadzone scaling and smoothing alpha factor, and directly commands `pyautogui.moveTo()`, `pyautogui.scroll()`, and `pyautogui.mouseDown()` (based on mouth distance threshold).
- **Voice Pipeline (`app/voice/voice_assist.py` & `speech_recognition.py`):** The `VoiceAssistant` coordinates continuous listening. The `SpeechRecognitionThread` captures chunks of audio, processes them through `SileroVAD` to find speech segments, passes segments to `WhisperEngine` to generate transcripts, and finally dispatches the text to the `CommandHandler`.
- **Command Engine (`app/voice/command_handler.py`):** Translates strings (e.g., "scroll down", "emergency stop", "lock computer") into executed Python functions. Includes fuzzy matching for misheard words and manages action execution state (cooldowns, toggles).
