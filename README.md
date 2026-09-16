# Face Gesture Assistant

> _Shared Repository for Final Year Project development and documentation._
> ðŸŽ“ **Academic Research:** Face Gesture Assistant is transitioning from an engineering prototype into an adaptive, multimodal research project. Track our progress in [RESEARCH_ROADMAP.md](./RESEARCH_ROADMAP.md).

**Face Gesture Assistant** is an accessible, fully **offline**, hands-free desktop control system that allows users to operate their computer entirely through **facial movements** and **voice commands**. It is built for individuals with motor disabilities or anyone who needs a completely touchless computing experience.

---

## ðŸ“‘ Table of Contents

1. [Project Overview](#-project-overview)
2. [Key Features](#-key-features)
3. [Technology Stack](#ï¸-technology-stack)
4. [System Architecture](#-system-architecture)
5. [Module Breakdown](#-module-breakdown)
6. [Voice Commands Reference](#ï¸-voice-commands-reference)
7. [GUI Features](#ï¸-gui-features)
8. [OS Compatibility](#-os-compatibility)
9. [Setup & Installation](#ï¸-setup--installation)
10. [Running the Application](#-running-the-application)
11. [Building a Standalone Executable](#-building-a-standalone-executable)
12. [Testing](#-testing)
13. [Project Structure](#-project-structure)
14. [Research Roadmap](#-research-roadmap)
15. [Contributing](#-contributing)

---

## ðŸŽ¯ Project Overview

Face Gesture Assistant (FGA) investigates an **adaptive, offline, multimodal control architecture** that:

- Personalizes interaction parameters to each user's motor behavior
- Arbitrates intelligently between facial gesture and voice inputs
- Measures accuracy, latency, false activations, and resource consumption
- Runs entirely on local hardware â€” **no cloud, no internet required**

The system is being developed as a **Final Year Engineering Project / Research Thesis** by Group 7.

---

## âœ¨ Key Features

| Feature | Description |
|---|---|
| ðŸŽ¥ **Face-Tracking Mouse** | Moves the cursor in real-time by tracking your nose bridge via webcam |
| ðŸ‘„ **Mouth-Click System** | Opens mouth to left-click â€” replaces a physical mouse button |
| ðŸ—£ï¸ **Offline Voice Control** | Full voice command pipeline with noise cancellation, VAD, and local Whisper ASR |
| ðŸªŸ **Window Management** | Switch, minimize, maximize, move, or close windows entirely by voice |
| ðŸ“± **Dynamic App Launcher** | Launch any installed Windows application by voice â€” no hardcoded paths |
| ðŸ”’ **GUI Power Controls** | Lock, sleep, restart, or shutdown the PC with safe graphical confirmation dialogs |
| ðŸ“ **Voice Dictation Mode** | Transcribe speech directly as keyboard input into any application |
| ðŸ†˜ **Emergency Stop** | Instantly halt all automation with a single voice command |
| ðŸŽ›ï¸ **Modern Dashboard** | Sleek dark-mode PySide6 UI with status indicators and quick controls |
| ðŸ”§ **Adaptive Calibration** | Personalize head-tracking sensitivity and mouth-click threshold per user |

---

## ðŸ› ï¸ Technology Stack

Face Gesture Assistant is built using modern, efficient libraries tailored for real-time processing and offline-first operation:

### Core Language
- **Python 3.10+**

### User Interface
| Library | Purpose |
|---|---|
| **PySide6** | Qt-based cross-platform GUI â€” dark-mode dashboard, dialogs, overlays |

### Computer Vision
| Library | Purpose |
|---|---|
| **OpenCV** (`opencv-python`, `opencv-contrib-python`) | Webcam capture and video frame processing |
| **MediaPipe** | Google's ML framework â€” Face Landmark detection (468 landmarks) for nose tracking and mouth state |

### Speech & Audio
| Library | Purpose |
|---|---|
| **SoundDevice** | Low-latency microphone audio capture |
| **pywebrtc-audio** | WebRTC APM â€” noise suppression, echo cancellation, automatic gain control |
| **Silero VAD** | Neural network Voice Activity Detector â€” isolates speech segments precisely |
| **Faster-Whisper** | Fully offline ASR using quantized INT8 Whisper models â€” fast, accurate transcription |
| **RapidFuzz** | Fuzzy string matching â€” maps imperfect transcripts to known commands |

### System Automation
| Library | Purpose |
|---|---|
| **PyAutoGUI** | Mouse movement, clicks, keyboard strokes simulation |
| **pynput** | Additional input listening and low-level input control |
| **pywin32** | Windows Win32 APIs â€” window management (focus, minimize, maximize, move) |
| **psutil** | System process information for app detection |

### Dev & Testing
| Library | Purpose |
|---|---|
| **pytest** | Test suite runner |
| **python-dotenv** | Environment variable management |

---

## ðŸ“Š System Architecture

Face Gesture Assistant implements an **Adaptive, Offline, Multimodal Control Architecture**. Rather than running face tracking and voice recognition as completely independent silos, FGA uses a **Multimodal Intent Manager** to arbitrate between modalities, apply dynamic calibration, and run safety validations before executing any action.

### Overall System Flow

```mermaid
graph TD
    A[FGA Dashboard UI] --> B[System Controller]
    B --> C{Activate Pipelines}

    subgraph Modality: Face Tracking
    C --> D[OpenCV Video Capture]
    D --> E[MediaPipe Face Landmarker]
    E --> F[Adaptive Calibration & Smoothing]
    F --> G[Cursor Tracking & Mouth Gestures]
    end

    subgraph Modality: Voice Recognition
    C --> H[Microphone Capture]
    H --> I[WebRTC APM + Silero VAD]
    I --> J[Faster-Whisper Local ASR]
    J --> K[Command Ontology & Fuzzy Correction]
    end

    G --> L((Multimodal Intent Manager))
    K --> L

    L --> M{Safety Validation}
    M -- Low Risk: Move / Scroll --> N[Execute Action via PyAutoGUI / pywin32]
    M -- High Risk: Close / Power --> O[GUI Confirmation Dialog]
    O -- Confirmed --> N
    O -- Cancelled --> P[No Action]
```

### Voice Command Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant AudioCapture
    participant WebRTC_VAD
    participant Whisper
    participant CommandHandler
    participant PyAutoGUI

    User->>AudioCapture: Speaks command (e.g., "scroll down")
    AudioCapture->>WebRTC_VAD: Raw audio frames
    WebRTC_VAD->>WebRTC_VAD: Noise suppression + VAD segmentation
    WebRTC_VAD->>Whisper: Isolated speech segment (NumPy array)
    Whisper->>CommandHandler: Transcript string: "scroll down"
    CommandHandler->>CommandHandler: Deduplicate + Fuzzy match
    CommandHandler->>PyAutoGUI: pyautogui.scroll(-500)
    PyAutoGUI-->>User: Screen scrolls down
```

### Face Tracking Flow

```mermaid
sequenceDiagram
    participant Webcam
    participant OpenCV
    participant MediaPipe
    participant Calibration
    participant Cursor

    Webcam->>OpenCV: Raw video frame
    OpenCV->>MediaPipe: Preprocessed frame
    MediaPipe->>Calibration: 468 Face Landmarks (nose tip coords)
    Calibration->>Calibration: Adaptive smoothing + range normalization
    Calibration->>Cursor: Translated (x, y) screen coordinates
    Cursor->>Cursor: pyautogui.moveTo(x, y)
    MediaPipe->>Cursor: Mouth Aspect Ratio (MAR) > threshold â†’ click()
```

---

## ðŸ—‚ï¸ Module Breakdown

The `app/` directory is organized into focused, single-responsibility modules:

```
app/
â”œâ”€â”€ main.py                          # Entry point â€” launches the Qt application
â”œâ”€â”€ camera/                          # Face tracking & computer vision
â”‚   â”œâ”€â”€ camera.py                        # Webcam capture manager
â”‚   â”œâ”€â”€ face_tracker.py                  # High-level face tracking coordinator
â”‚   â”œâ”€â”€ face_cursor_windows_varient.py   # Windows-optimized cursor mapping
â”‚   â”œâ”€â”€ face_cursor_wayland.py           # Wayland (Linux) cursor mapping
â”‚   â”œâ”€â”€ facecursor.py                    # Core cursor translation logic
â”‚   â”œâ”€â”€ EXP.py / EXPs.py                # Experimental calibration scripts
â”‚   â””â”€â”€ face_landmarker.task            # Bundled MediaPipe model file (~3.6 MB)
â”œâ”€â”€ voice/                           # Full speech recognition pipeline
â”‚   â”œâ”€â”€ audio_capture.py                 # Microphone stream management (SoundDevice)
â”‚   â”œâ”€â”€ audio_processor.py               # WebRTC APM preprocessing
â”‚   â”œâ”€â”€ vad.py                           # Silero VAD â€” speech segmentation
â”‚   â”œâ”€â”€ whisper_engine.py                # Faster-Whisper transcription engine
â”‚   â”œâ”€â”€ speech_recognition.py            # Orchestrates audio â†’ VAD â†’ Whisper
â”‚   â”œâ”€â”€ command_handler.py               # Maps transcripts to actions (RapidFuzz)
â”‚   â””â”€â”€ voice_assist.py                  # High-level voice assistant controller
â”œâ”€â”€ gestures/                        # Gesture detection layer
â”‚   â”œâ”€â”€ gesture_detector.py              # Unified gesture event dispatcher
â”‚   â”œâ”€â”€ head_tracking.py                 # Head movement â†’ cursor position
â”‚   â””â”€â”€ mouth_detection.py               # Mouth Aspect Ratio â†’ click events
â”œâ”€â”€ control/                         # System automation layer
â”‚   â”œâ”€â”€ mouse_control.py                 # Mouse movement and click actions
â”‚   â”œâ”€â”€ keyboard_control.py              # Keyboard simulation and text input
â”‚   â””â”€â”€ window_control.py               # Window focus, minimize, maximize (pywin32)
â”œâ”€â”€ core/                            # Application core & settings
â”‚   â”œâ”€â”€ command_engine.py                # Central command dispatcher
â”‚   â””â”€â”€ settings.py                      # Global config and user preferences
â”œâ”€â”€ ui/                              # PySide6 user interface
â”‚   â”œâ”€â”€ main_window.py                   # Primary dashboard window
â”‚   â”œâ”€â”€ dashboard.py                     # Dashboard widget layout
â”‚   â”œâ”€â”€ voice_overlay.py                 # Live voice transcript HUD overlay
â”‚   â”œâ”€â”€ calibration_ui.py                # Calibration wizard UI
â”‚   â”œâ”€â”€ learn_dialog.py                  # Command learning / help dialog
â”‚   â””â”€â”€ wizard_dialog.py                 # First-run setup wizard
â”œâ”€â”€ system/                          # System-level integrations
â””â”€â”€ utils/                           # Shared utilities and helpers
```

---

## ðŸ—£ï¸ Voice Commands Reference

Face Gesture Assistant supports a comprehensive set of voice commands covering every aspect of desktop control:

### ðŸ–±ï¸ Mouse & Scrolling

| Command | Action |
|---|---|
| `"click"` | Left mouse click |
| `"double click"` | Double left click |
| `"right click"` | Right mouse click |
| `"scroll down"` / `"down"` | Scroll page down |
| `"scroll up"` / `"up"` | Scroll page up |
| `"scroll faster"` / `"scroll slower"` | Adjust scroll speed |
| `"stop scrolling"` | Halt auto-scroll |

### ðŸŒ Browser & Tabs

| Command | Action |
|---|---|
| `"go back"` / `"go forward"` | Browser navigation |
| `"refresh"` | Reload current page |
| `"new tab"` / `"close tab"` | Tab management |
| `"next tab"` / `"previous tab"` | Tab switching |
| `"history"` / `"downloads"` / `"bookmarks"` | Open browser panels |

### ðŸ” Zoom

| Command | Action |
|---|---|
| `"zoom in"` / `"zoom out"` | Browser zoom |
| `"reset zoom"` | Reset to 100% |

### ðŸŒ Websites & Search

| Command | Action |
|---|---|
| `"open youtube"`, `"open reddit"`, `"open github"`, etc. | Open website in browser |
| `"open chrome"`, `"open notepad"`, `"open calculator"` | Launch application |
| `"search [query]"` | Google search for the query |

> **Dynamic App Launcher:** Beyond hardcoded apps, BUG dynamically discovers any installed Windows application. Say `"open [app name]"` for any installed program â€” no configuration needed. Safely gated behind `open`, `launch`, or `start` keywords to prevent accidental launches.

### ðŸ“‹ Text & Clipboard

| Command | Action |
|---|---|
| `"copy"` / `"paste"` / `"cut"` | Clipboard operations |
| `"undo"` / `"redo"` | Edit history |
| `"select all"` | Select all text |
| `"delete word"` | Delete previous word |
| `"select next word"` / `"select previous word"` | Word selection |
| `"start of line"` / `"end of line"` | Line navigation |

### âŒ¨ï¸ Keyboard Keys

| Command | Action |
|---|---|
| `"press enter"` / `"press tab"` / `"press escape"` | Key presses |
| `"backspace"` | Delete character |
| `"yes"` / `"no"` / `"cancel"` | Confirmation responses |

### ðŸªŸ Window Management

| Command | Action |
|---|---|
| `"switch to [app]"` | Bring app window to foreground |
| `"minimize [app]"` / `"maximize [app]"` | Resize specific window |
| `"move window left/right/up/down"` | Move active window 100px |
| `"close this window"` | Close the active window |
| `"switch window"` | Alt+Tab |
| `"fullscreen"` | Toggle fullscreen |

### âš¡ System & Power

| Command | Action | Confirmation |
|---|---|---|
| `"lock computer"` | Lock Windows session | âœ… GUI popup |
| `"sleep computer"` | Put PC to sleep | âœ… GUI popup |
| `"restart computer"` | Restart the PC | âœ… GUI popup |
| `"shutdown computer"` | Shut down the PC | âœ… GUI popup |
| `"open start menu"` | Open Windows Start Menu | â€” |
| `"open task manager"` | Open Task Manager | â€” |
| `"save"` / `"save as"` / `"new file"` / `"open file"` | File operations | â€” |

### ðŸŽµ Media Controls

| Command | Action |
|---|---|
| `"play"` / `"pause"` | Media play/pause |
| `"mute"` / `"unmute"` | Audio mute toggle |
| `"volume up"` / `"volume down"` | Volume adjustment |
| `"skip forward"` / `"skip back"` | Media seek |
| `"next video"` | Next media item |

### ðŸ“  Dictation Mode

| Command | Action |
|---|---|
| `"start typing"` | Enter dictation mode â€” speech is typed directly as keyboard input |
| `"stop typing"` | Exit dictation mode |

### ðŸŽ›ï¸  Tracking & Calibration

| Command | Action |
|---|---|
| `"enable head tracking"` / `"disable head tracking"` | Toggle face cursor |
| `"enable mouth click"` / `"disable mouth click"` | Toggle mouth-click |
| `"calibrate"` | Run full calibration wizard |
| `"calibrate mouth"` | Recalibrate mouth-click threshold |
| `"reset calibration"` | Restore default calibration |

### ðŸ†˜ Safety

| Command | Action |
|---|---|
| `"emergency stop"` | **Immediately disables all automation** |
| `"enable control"` | Resumes automation after emergency stop |
| `"help"` | Open the command reference dialog |

---

## ðŸ–¥ï¸  GUI Features

### Main Dashboard
The PySide6 dark-mode dashboard provides:
- **Large, high-contrast control buttons** â€” Start All Systems, Stop All, individual pipeline toggles
- **Live status indicators** â€” Camera, Voice, and Tracking state chips
- **Real-time voice transcript overlay** — see what FGA heard in a floating HUD
- **Settings and calibration access** from the toolbar

### Voice Overlay
A transparent floating window that appears when voice is active, showing the last recognized command in real-time for immediate feedback.

### Calibration Wizard
Step-by-step guided setup for:
- **Head tracking calibration** â€” sets the neutral center point and sensitivity range
- **Mouth-click calibration** â€” measures resting mouth distance and sets the open/click threshold

### GUI Power Confirmation Dialogs

For high-risk power commands, BUG uses a **safe graphical dialog** instead of voice confirmation (which is unreliable due to Whisper misrecognition):

```
User: "restart computer"
           â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              Confirm Restart                   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                              â”‚
â”‚  Are you sure you want to restart the        â”‚
â”‚  computer?                                   â”‚
â”‚                                              â”‚
â”‚        [ YES ]          [ NO ]              â”‚
â”‚                                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
           â†“
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”
   â–¼               â–¼
Click YES       Click NO
   â”‚               â”‚
   â–¼               â–¼
Action Executes  Cancelled
```

**Technical implementation:**
- Uses Qt Signals for thread-safe communication between voice thread and GUI main thread
- `QMessageBox` for a professional, consistent modal dialog
- Modal dialog blocks all other input until resolved
- Emergency stop remains active even while dialog is open

**Safety features:**
- âœ… No voice confirmation â€” eliminates Whisper misrecognition risk
- âœ… Graphical YES/NO buttons only
- âœ… Modal dialog â€” must click to continue
- âœ… Dialog appears on top of all windows
- âœ… Emergency stop still functional

---

## ðŸ’» OS Compatibility

| OS | Status | Notes |
|---|---|---|
| **Windows 10 / 11** | âœ… Fully supported | All features work out of the box |
| **Linux â€” X11 Session** | âœ… Fully supported | Use Wayland scripts in `app/camera/` |
| **Linux â€” Wayland Session** | âš ï¸ Partial | Camera, UI, and voice work; `pyautogui` mouse control fails due to Wayland's security model |
| **macOS** | âŒ Not tested | `pywin32` (Windows-only) is unavailable |

> **Wayland users:** Run the experimental Wayland-compatible cursor scripts located in `app/camera/`.

---

## ðŸ› ï¸ Setup & Installation

### Prerequisites
- **Python 3.10 or higher**
- A **webcam** (for face tracking)
- A **microphone** (for voice commands)
- **Windows 10/11** recommended (or Linux with X11)

### 1. Clone the Repository

```bash
git clone https://github.com/maj-afe/Group-7-s-Projects-Repository.git
cd Group-7-s-Projects-Repository
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
```

**Activate the environment:**

```powershell
# Windows (PowerShell)
.\.venv\Scripts\activate
```

```bash
# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** On first launch, **Faster-Whisper** and **Silero VAD** will automatically download their required model files into the `models/` directory. An internet connection is only needed for this initial download.

### 4. MediaPipe Model (Bundled)

The MediaPipe Face Landmarker model (`face_landmarker.task`, ~3.6 MB) is already bundled in `app/camera/` â€” no separate download required.

---

## ðŸƒ Running the Application

### Using the Helper Script (Recommended)

```powershell
.\run.ps1
```

### Direct Python Launch

```bash
python app/main.py
```

Once the dashboard opens:
1. Click **"Start All Systems"** to activate both the camera and voice pipelines simultaneously.
2. Or use the individual **"Start Camera"** / **"Start Voice"** buttons to enable pipelines independently.
3. Use **"Calibrate"** on first run to set your personal head-tracking and mouth-click sensitivity.

---

## ðŸ“¦ Building a Standalone Executable

Face Gesture Assistant can be packaged into a single `.exe` using PyInstaller â€” no Python installation required on the target machine.

### Steps

1. Ensure dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the build script:
   ```powershell
   .\build.ps1
   ```

3. The executable is generated at:
   ```
   dist\BUG_Dashboard.exe
   ```

> **Note:** The executable is large (~400 MB) because it bundles PyTorch, OpenCV, and MediaPipe. On first run, it will download required AI models to your local user folder.

The build configuration is defined in [`BUG_Dashboard.spec`](./BUG_Dashboard.spec).

---

## ðŸ§ª Testing

Face Gesture Assistant includes a dedicated test suite in the `tests/` directory:

| Test File | Coverage |
|---|---|
| `test_commands.py` | Voice command mapping and fuzzy matching logic |
| `test_audio.py` | Audio capture and pipeline integrity |
| `test_vad.py` | Voice Activity Detection accuracy |
| `test_accuracy.py` | End-to-end command recognition accuracy metrics |

### Running Tests

```bash
# Run the full test suite
pytest tests/

# Run a specific test file with verbose output
pytest tests/test_commands.py -v

# Run with short traceback
pytest tests/ --tb=short
```

### Smoke Tests

Quick sanity checks available at the root level:

```bash
python _smoke.py            # General system smoke test
python _transcribe_test.py  # Whisper transcription smoke test
```

---

## ðŸ“ Project Structure

```
Group-7-s-Projects-Repository/
â”‚
â”œâ”€â”€ app/                          # Main application source
â”‚   â”œâ”€â”€ main.py                   # Entry point
â”‚   â”œâ”€â”€ camera/                   # Face tracking & computer vision
â”‚   â”œâ”€â”€ voice/                    # Speech recognition pipeline
â”‚   â”œâ”€â”€ gestures/                 # Gesture event detection
â”‚   â”œâ”€â”€ control/                  # System automation (mouse, keyboard, windows)
â”‚   â”œâ”€â”€ core/                     # Command engine & settings
â”‚   â”œâ”€â”€ ui/                       # PySide6 GUI components
â”‚   â”œâ”€â”€ system/                   # System-level integrations
â”‚   â””â”€â”€ utils/                    # Shared utilities
â”‚
â”œâ”€â”€ models/                       # Downloaded AI model files (auto-populated on first run)
â”œâ”€â”€ tests/                        # Pytest test suite
â”œâ”€â”€ whisper.cpp/                  # Git submodule â€” whisper.cpp for benchmarking
â”œâ”€â”€ _whisper_stubs/               # Type stubs for Whisper
â”‚
â”œâ”€â”€ requirements.txt              # Python dependencies
â”œâ”€â”€ run.ps1                       # Quick-launch PowerShell script
â”œâ”€â”€ build.ps1                     # PyInstaller build script
â”œâ”€â”€ BUG_Dashboard.spec            # PyInstaller spec file
â”œâ”€â”€ _smoke.py                     # System smoke test
â”œâ”€â”€ _transcribe_test.py           # Whisper transcription test
â”œâ”€â”€ RESEARCH_ROADMAP.md           # Thesis goals and research progress
â””â”€â”€ README.md                     # This file
```

---

## ðŸ”¬ Research Roadmap

Face Gesture Assistant is actively evolving as a research project. The five core research contributions are:

| # | Contribution | Status |
|---|---|---|
| 1 | **Adaptive Personal Calibration** â€” Dynamic sensitivity based on user's motor range | ðŸ”„ In Progress |
| 2 | **Cross-modal Intent Arbitration** â€” Multimodal Intent Manager merging face + voice | ðŸ”„ In Progress |
| 3 | **False-Action & Safety Suppression** â€” Risk classification + GUI confirmation policies | âœ… Partial (Emergency Stop done) |
| 4 | **Offline Resource Efficiency** â€” Benchmarking Whisper.cpp vs Faster-Whisper vs Vosk | âœ… Partial (Faster-Whisper deployed) |
| 5 | **User Evaluation** â€” Formal trials measuring target acquisition time, throughput, workload | â³ To Do |

For full details, task breakdowns, and the thesis statement, see **[RESEARCH_ROADMAP.md](./RESEARCH_ROADMAP.md)**.

---

## ðŸ¤ Contributing

This is a Final Year Project repository maintained by **Group 7**. To contribute:

1. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes with a clear message:
   ```bash
   git commit -m "feat: describe what you did"
   ```
3. Push and open a Pull Request against `main`.
4. Ensure all tests pass before requesting review:
   ```bash
   pytest tests/
   ```

---

<div align="center">

**Face Gesture Assistant** — Built with ❤️ by Group 7 | Final Year Project

_Making computing accessible, one gesture at a time._

</div>
