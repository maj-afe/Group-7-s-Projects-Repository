import math
import time
import cv2
import mediapipe as mp

from evdev import ecodes, UInput, AbsInfo
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Display resolution
SCREEN_W, SCREEN_H = 1280, 720

# Define absolute axis configurations using AbsInfo objects
cap_events = {
    ecodes.EV_ABS: [
        (ecodes.ABS_X, AbsInfo(value=int(SCREEN_W / 2), min=0, max=SCREEN_W, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_Y, AbsInfo(value=int(SCREEN_H / 2), min=0, max=SCREEN_H, fuzz=0, flat=0, resolution=0)),
    ],
    ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT],
}

try:
    ui = UInput(cap_events, name="Nutshell-Virtual-Mouse", version=0x3)
except PermissionError:
    print("[ERROR] Permission denied accessing /dev/uinput. Ensure your user is in 'input' group.")
    exit(1)

# Initialize MediaPipe Task
base_options = python.BaseOptions(model_asset_path="/home/aniruddh_sen/Documents/VSC/PYthon/face-cursor-wayland/face_landmarker.task")
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.7,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

cam = cv2.VideoCapture(0)

# Calibration state
calibrated = False
center_x, center_y = 0.5, 0.5
deadzone_scale = 0.12  # Sensitivity: lower = more responsive

# Position tracking variables
smooth_x = SCREEN_W / 2
smooth_y = SCREEN_H / 2
alpha = 0.26  # Smoothing factor

# Mouth Click Thresholds & Debounce State
MOUTH_OPEN_THRESHOLD = 0.035  # Distance between upper/lower lip to trigger click
is_mouth_open = False


def set_absolute_position(x, y):
    """Dispatches exact screen coordinates directly to uinput."""
    ui.write(ecodes.EV_ABS, ecodes.ABS_X, int(x))
    ui.write(ecodes.EV_ABS, ecodes.ABS_Y, int(y))
    ui.syn()


def trigger_click(state):
    """Sends press (True) or release (False) events for BTN_LEFT."""
    ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1 if state else 0)
    ui.syn()


print("[INFO] Wayland Session Active. Look straight at your screen and press 'c' to set screen center.")

while cam.isOpened():
    success, frame = cam.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(time.time() * 1000)
    results = landmarker.detect_for_video(mp_image, timestamp_ms)

    key = cv2.waitKey(1) & 0xFF

    if results.face_landmarks:
        landmarks = results.face_landmarks[0]
        anchor_point = landmarks[168]  # Bridge of the nose

        # Mouth landmarks: 13 (inner upper lip), 14 (inner lower lip)
        upper_lip = landmarks[13]
        lower_lip = landmarks[14]

        # Calculate Euclidean distance between lips
        mouth_distance = math.hypot(upper_lip.x - lower_lip.x, upper_lip.y - lower_lip.y)

        # Recalibrate: Set neutral position on 'c'
        if key == ord("c"):
            center_x, center_y = anchor_point.x, anchor_point.y
            smooth_x = SCREEN_W / 2
            smooth_y = SCREEN_H / 2
            set_absolute_position(smooth_x, smooth_y)
            calibrated = True
            print(f"[CALIBRATED] Neutral set -> X: {center_x:.3f}, Y: {center_y:.3f}")

        if calibrated:
            # --- CURSOR MOVEMENT ---
            dx = anchor_point.x - center_x
            dy = anchor_point.y - center_y

            target_x = (SCREEN_W / 2) + (dx / deadzone_scale) * (SCREEN_W / 2)
            target_y = (SCREEN_H / 2) + (dy / deadzone_scale) * (SCREEN_H / 2)

            target_x = max(0, min(SCREEN_W - 1, target_x))
            target_y = max(0, min(SCREEN_H - 1, target_y))

            smooth_x = alpha * target_x + (1 - alpha) * smooth_x
            smooth_y = alpha * target_y + (1 - alpha) * smooth_y

            set_absolute_position(smooth_x, smooth_y)

            # --- MOUTH CLICK LOGIC ---
            if mouth_distance > MOUTH_OPEN_THRESHOLD:
                if not is_mouth_open:
                    is_mouth_open = True
                    trigger_click(True)  # Mouse Down
                    print("[CLICK] Mouth Opened -> Left Mouse Down")
            else:
                if is_mouth_open:
                    is_mouth_open = False
                    trigger_click(False)  # Mouse Up
                    print("[RELEASE] Mouth Closed -> Left Mouse Up")

            # --- VISUAL FEEDBACK ---
            # Green dot for nose anchor point
            cv2.circle(frame, (int(anchor_point.x * w), int(anchor_point.y * h)), 5, (0, 255, 0), -1)

            # Red dot when clicking, Blue dot when mouth is closed
            lip_color = (0, 0, 255) if is_mouth_open else (255, 0, 0)
            cv2.circle(frame, (int(upper_lip.x * w), int(upper_lip.y * h)), 4, lip_color, -1)
            cv2.circle(frame, (int(lower_lip.x * w), int(lower_lip.y * h)), 4, lip_color, -1)

    cv2.imshow("Nutshell Arch Wayland Prototype", frame)

    if key == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
landmarker.close()
ui.close()
