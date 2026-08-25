# BUG - Hands-Free Browsing Assistant

_Shared Repository for Final Year project development and documentation._

BUG is an accessible, hands-free browsing assistant designed to let users control their computer using facial movements and voice commands. It features a modern desktop UI built with PySide6 that seamlessly connects computer vision and speech recognition pipelines.

## 🛠️ Technology Stack

BUG is built using modern and efficient libraries tailored for real-time processing and offline capabilities:

- **Core Language**: Python 3
- **User Interface**: PySide6 (Qt for Python) - For building a sleek, responsive, modern dark-mode dashboard.
- **Computer Vision**:
  - OpenCV (`opencv-python`) - For capturing and processing webcam video streams.
  - MediaPipe - Google's ML framework used for precise Face Landmark detection (nose tracking, mouth state).
- **Speech & Audio**:
  - SoundDevice (`sounddevice`) - For capturing low-latency audio streams from the microphone.
  - WebRTC Audio Processing (`pywebrtc-audio`) - For noise suppression, acoustic echo cancellation, and automatic gain control.
  - Silero VAD (`silero-vad`) - A fast, neural-network-based Voice Activity Detector to perfectly segment speech.
  - Faster-Whisper (`faster-whisper`) - For fully offline, highly accurate, and fast speech transcription.
  - RapidFuzz (`rapidfuzz`) - For lightning-fast fuzzy matching of transcripts to system commands.
- **System Automation**:
  - PyAutoGUI - For simulating mouse movements, clicks, and keyboard strokes.
  - pynput - Additional input listening and manipulation.

## 🚀 Detailed Features

### 1. Face-Tracking Mouse Control

Uses your webcam and Google's MediaPipe Face Landmarker to track your nose bridge and translate it into smooth cursor movements. The mapping dynamically translates physical head movements to screen coordinates, allowing you to navigate seamlessly across the entire display.

### 2. Mouth-Click System

Automatically triggers left-clicks when you open your mouth. It calculates the Mouth Aspect Ratio (MAR) in real-time, instantly firing a click event when the ratio crosses a predefined threshold, effectively replacing a physical mouse button.

### 3. Offline Voice Recognition

Integrated with a state-of-the-art voice pipeline designed for noisy environments, working entirely offline for absolute privacy.

- _Acoustic Cleaning_: The microphone feed passes through WebRTC APM to cancel echo and suppress background noise.
- _Voice Activity Detection_: Silero VAD isolates exact speech segments, preventing the transcriber from processing silence or background noise.
- _Real-time Transcription_: Faster-Whisper (using the `base` int8 model) transcribes speech segments quickly and accurately.
- _Fuzzy Command Matching_: The transcript goes through deduplication logic and RapidFuzz to match spoken intents even if the transcript is slightly imperfect.

### 4. Modern Dashboard UI

A sleek, dark-mode PySide6 interface designed specifically for accessibility. It provides massive, high-contrast buttons, system status indicators, and a minimalist layout to prevent distraction. Includes controls to independently start/stop vision and voice systems.

## 🗣️ Available Voice Commands

- **Mouse & Scrolling**: `"click"`, `"double click"`, `"right click"`, `"scroll down"`, `"scroll up"`, `"scroll faster"`, `"scroll slower"`, `"stop scrolling"`, `"up"`, `"down"`
- **Browser & Tabs**: `"go back"`, `"go forward"`, `"refresh"`, `"new tab"`, `"close tab"`, `"next tab"`, `"previous tab"`, `"history"`, `"downloads"`, `"bookmarks"`
- **Zoom**: `"zoom in"`, `"zoom out"`, `"reset zoom"`
- **Websites & Search**: `"open chrome"`, `"open youtube"`, `"open reddit"`, `"open facebook"`, `"open instagram"`, `"open github"`, `"open chat gpt"`, `"open netflix"`, `"open amazon"`, `"search [query]"`
- **Text & Clipboard**: `"copy"`, `"paste"`, `"cut"`, `"undo"`, `"redo"`, `"select all"`, `"delete word"`, `"select next word"`, `"select previous word"`, `"start of line"`, `"end of line"`
- **Keyboard Keys**: `"press enter"`, `"press tab"`, `"press escape"`, `"backspace"`, `"yes"`, `"no"`, `"cancel"`
- **System & Files**: `"save"`, `"save as"`, `"new file"`, `"open file"`, `"open notepad"`, `"open calculator"`, `"open start menu"`, `"open task manager"`, `"lock computer"`, `"help"`
- **Media Controls**: `"play"`, `"pause"`, `"mute"`, `"unmute"`, `"volume up"`, `"volume down"`, `"skip forward"`, `"skip back"`, `"next video"`
- **Window Management**: `"switch window"`, `"minimize window"`, `"close window"`, `"fullscreen"`
- **Dictation**: `"start typing"`, `"stop typing"` (transcribes speech directly as keyboard input)
- **Tracking & Calibration**: `"enable/disable head tracking"`, `"enable/disable mouth click"`, `"calibrate"`, `"calibrate mouth"`, `"reset calibration"`
- **Safety**: `"emergency stop"` (stops all automation immediately), `"enable control"` (resumes after an emergency stop)

## 📊 System Architecture & Flowcharts

The system consists of two primary asynchronous pipelines running simultaneously alongside the PySide6 main event loop.

### Overall System Flow

```mermaid
graph TD
    A[BUG Dashboard UI] --> B[System Controller]
    B --> C{Activate Pipelines}

    subgraph Computer Vision Pipeline
    C --> D[OpenCV Video Capture]
    D --> E[MediaPipe Face Landmarker]
    E --> F{Face Detected?}
    F -- Yes --> G[Calculate Nose Coordinates]
    F -- Yes --> H[Calculate Mouth Aspect Ratio]
    G --> I[PyAutoGUI Mouse Move]
    H --> J{Mouth Open?}
    J -- Yes --> K[PyAutoGUI Left Click]
    end

    subgraph Voice Recognition Pipeline
    C --> L[SoundDevice Audio Capture]
    L --> M[WebRTC Audio Processing]
    M --> N[Silero VAD]
    N --> O{Speech Segmented?}
    O -- Yes --> P[Faster-Whisper]
    P --> Q[Text Normalization & Dedup]
    Q --> R[RapidFuzz Matcher]
    R --> S{Command Found?}
    S -- Yes --> T[Execute PyAutoGUI / Subprocess]
    end
```

### Voice Command Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant AudioCapture
    participant VAD
    participant Whisper
    participant CommandHandler
    participant PyAutoGUI

    User->>AudioCapture: Speaks command (e.g., "scroll down")
    AudioCapture->>VAD: Cleaned Audio Frames
    VAD->>Whisper: Complete Speech Segment (NumPy array)
    Whisper->>CommandHandler: Text String: "scroll down"
    CommandHandler->>CommandHandler: Deduplicate and Fuzzy Match
    CommandHandler->>PyAutoGUI: Execute PyAutoGUI.scroll(-500)
    PyAutoGUI-->>User: Screen scrolls down
```

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
   # On Windows (Powershell)
   .\.venv\Scripts\activate
   # On Mac/Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Faster-Whisper and Silero VAD will automatically download their required model files to `models/` upon the first launch.)*

## 🏃 Running the Application

To launch the BUG dashboard, simply run the main entry point:

```bash
.\run.ps1
```

*(Alternatively, run `python app/main.py` if not using the helper script)*

From the dashboard, you can click **"Start All Systems"** to activate the camera and voice pipelines!
