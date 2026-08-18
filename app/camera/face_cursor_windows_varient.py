import math
import os
import time
import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Dynamically construct the absolute path relative to this script file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "face_landmarker.task")

# Disable pyautogui safety pause/failsafe for real-time cursor control
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# Fetch native Windows display resolution automatically
SCREEN_W, SCREEN_H = pyautogui.size()

# Initialize MediaPipe Task with absolute path and VIDEO mode
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
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
alpha = 0.25  # Smoothing factor

# Mouth Click Thresholds & State
MOUTH_OPEN_THRESHOLD = 0.035
is_mouth_open = False

print(
    "[INFO] Windows Session Active. Look straight at your screen and press 'c'"
    " to set screen center."
)

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

        # Calculate distance between lips
        mouth_distance = math.hypot(
            upper_lip.x - lower_lip.x, upper_lip.y - lower_lip.y
        )

        # Recalibrate: Set neutral position on 'c'
        if key == ord("c"):
            center_x, center_y = anchor_point.x, anchor_point.y
            smooth_x = SCREEN_W / 2
            smooth_y = SCREEN_H / 2
            pyautogui.moveTo(int(smooth_x), int(smooth_y))
            calibrated = True
            print(
                f"[CALIBRATED] Neutral set -> X: {center_x:.3f}, Y: {center_y:.3f}"
            )

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

            # Windows-compatible mouse movement
            pyautogui.moveTo(int(smooth_x), int(smooth_y))

            # --- MOUTH CLICK LOGIC ---
            if mouth_distance > MOUTH_OPEN_THRESHOLD:
                if not is_mouth_open:
                    is_mouth_open = True
                    pyautogui.mouseDown(button="left")
                    print("[CLICK] Mouth Opened -> Left Mouse Down")
            else:
                if is_mouth_open:
                    is_mouth_open = False
                    pyautogui.mouseUp(button="left")
                    print("[RELEASE] Mouth Closed -> Left Mouse Up")

            # --- VISUAL FEEDBACK ---
            cv2.circle(
                frame,
                (int(anchor_point.x * w), int(anchor_point.y * h)),
                5,
                (0, 255, 0),
                -1,
            )
            lip_color = (0, 0, 255) if is_mouth_open else (255, 0, 0)
            cv2.circle(
                frame,
                (int(upper_lip.x * w), int(upper_lip.y * h)),
                4,
                lip_color,
                -1,
            )
            cv2.circle(
                frame,
                (int(lower_lip.x * w), int(lower_lip.y * h)),
                4,
                lip_color,
                -1,
            )

    cv2.imshow("Nutshell Windows Prototype", frame)

    if key == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
landmarker.close()