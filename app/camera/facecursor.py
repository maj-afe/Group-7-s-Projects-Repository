import time
import cv2
import mediapipe as mp

from evdev import ecodes, UInput
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Screen resolution (matching your KDE Plasma display settings)
SCREEN_W, SCREEN_H = 720 , 480

# 1. Create native Linux uinput absolute virtual device
cap_events = {
    ecodes.EV_ABS: [
        (ecodes.ABS_X, (0, SCREEN_W, 0, 0)),
        (ecodes.ABS_Y, (0, SCREEN_H, 0, 0)),
    ],
    ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT],
}

try:
  ui = UInput(cap_events, name="Nutshell-Virtual-Mouse", version=0x3)
except PermissionError:
  print(
      "[ERROR] Permission denied accessing /dev/uinput. Ensure your user is in"
      " 'input' group."
  )
  exit(1)

# 2. Initialize MediaPipe Face Landmarker
base_options = python.BaseOptions(model_asset_path="face_landmarker.task")
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.7,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

cam = cv2.VideoCapture(0)

# Calibration state & tracking variables
calibrated = False
center_x, center_y = 0.5, 0.5
deadzone_scale = (
    0.12  # Range of head movement required to reach screen edges
)

smooth_x, smooth_y = SCREEN_W / 2, SCREEN_H / 2
alpha = 0.25  # Lower = smoother, higher = faster response


def set_absolute_position(x, y):
  """Dispatches exact screen coordinates directly to Linux kernel uinput."""
  ui.write(ecodes.EV_ABS, ecodes.ABS_X, int(x))
  ui.write(ecodes.EV_ABS, ecodes.ABS_Y, int(y))
  ui.syn()


print(
    "[INFO] Wayland Session Active. Look straight at screen and press 'c' to"
    " calibrate."
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

    # Recalibrate neutral point
    if key == ord("c"):
      center_x, center_y = anchor_point.x, anchor_point.y
      # Reset smooth values to center screen to avoid jump cut
      smooth_x, smooth_y = SCREEN_W / 2, SCREEN_H / 2
      calibrated = True
      print(
          f"[CALIBRATED] Center set -> X: {center_x:.3f}, Y:"
          f" {center_y:.3f}"
      )

    if calibrated:
      # Calculate movement offset from calibrated center
      dx = anchor_point.x - center_x
      dy = anchor_point.y - center_y

      # Map normalized offset to screen coordinates
      target_x = (SCREEN_W / 2) + (dx / deadzone_scale) * (SCREEN_W / 2)
      target_y = (SCREEN_H / 2) + (dy / deadzone_scale) * (SCREEN_H / 2)

      # Clamp to screen boundary limits
      target_x = max(0, min(SCREEN_W - 1, target_x))
      target_y = max(0, min(SCREEN_H - 1, target_y))

      # Exponential Moving Average for smoothing
      smooth_x = alpha * target_x + (1 - alpha) * smooth_x
      smooth_y = alpha * target_y + (1 - alpha) * smooth_y

      # Inject position directly
      set_absolute_position(smooth_x, smooth_y)

      # Draw tracking indicator
      cv2.circle(
          frame,
          (int(anchor_point.x * w), int(anchor_point.y * h)),
          6,
          (0, 255, 0),
          -1,
      )

  cv2.imshow("Nutshell Arch Wayland Prototype", frame)

  if key == ord("q"):
    break

cam.release()
cv2.destroyAllWindows()
landmarker.close()
ui.close()
