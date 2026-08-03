import math
import time
import cv2
import mediapipe as mp

from evdev import ecodes, UInput, AbsInfo
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Display resolution
SCREEN_W, SCREEN_H = 1280, 720


# --- One Euro Filter Class ---
class OneEuroFilter:

  def __init__(self, t0, x0, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
    self.min_cutoff = min_cutoff
    self.beta = beta
    self.d_cutoff = d_cutoff
    self.x_prev = x0
    self.dx_prev = 0.0
    self.t_prev = t0

  def _alpha(self, cutoff, dt):
    tau = 1.0 / (2 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)

  def filter(self, t, x):
    dt = t - self.t_prev
    if dt <= 0.0:
      return self.x_prev

    # Estimate derivative (speed of movement)
    dx = (x - self.x_prev) / dt
    dx_hat = self._alpha(self.d_cutoff, dt) * dx + (
        1 - self._alpha(self.d_cutoff, dt)
    ) * self.dx_prev

    # Dynamic cutoff based on speed
    cutoff = self.min_cutoff + self.beta * abs(dx_hat)
    a = self._alpha(cutoff, dt)
    x_hat = a * x + (1 - a) * self.x_prev

    # Update state
    self.x_prev = x_hat
    self.dx_prev = dx_hat
    self.t_prev = t

    return x_hat


# Define virtual absolute input device using AbsInfo
cap_events = {
    ecodes.EV_ABS: [
        (
            ecodes.ABS_X,
            AbsInfo(
                value=int(SCREEN_W / 2),
                min=0,
                max=SCREEN_W,
                fuzz=0,
                flat=0,
                resolution=0,
            ),
        ),
        (
            ecodes.ABS_Y,
            AbsInfo(
                value=int(SCREEN_H / 2),
                min=0,
                max=SCREEN_H,
                fuzz=0,
                flat=0,
                resolution=0,
            ),
        ),
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

# Initialize MediaPipe Task
base_options = python.BaseOptions(model_asset_path="face_landmarker.task")
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.7,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

cam = cv2.VideoCapture(0)

# Calibration & sensitivity states
calibrated = False
center_x, center_y = 0.5, 0.5
deadzone_scale = 0.12  # Range of motion scale

# One Euro Filter Instances
t_start = time.time()
filter_x = OneEuroFilter(
    t_start, SCREEN_W / 2, min_cutoff=0.1, beta=0.01  # Lower = stronger jitter control at rest
)  # Higher = faster tracking during quick head tilts
filter_y = OneEuroFilter(t_start, SCREEN_H / 2, min_cutoff=0.1, beta=0.01)

# Mouth Click Thresholds
# MOUTH_MAX==A
# MOUTH_MIN==N
MOUTH_OPEN_THRESHOLD = 0.0350
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
  now = time.time()
  timestamp_ms = int(now * 1000)
  results = landmarker.detect_for_video(mp_image, timestamp_ms)

  key = cv2.waitKey(1) & 0xFF

  if results.face_landmarks:
    landmarks = results.face_landmarks[0]
    anchor_point = landmarks[168]  # Bridge of nose
    upper_lip = landmarks[13]
    lower_lip = landmarks[14]

    mouth_distance = math.hypot(
        upper_lip.x - lower_lip.x, upper_lip.y - lower_lip.y
    )

    # Recalibrate neutral center on 'c'
    if key == ord("c"):
      center_x, center_y = anchor_point.x, anchor_point.y
      filter_x = OneEuroFilter(now, SCREEN_W / 2, min_cutoff=0.1, beta=0.01)
      filter_y = OneEuroFilter(now, SCREEN_H / 2, min_cutoff=0.1, beta=0.01)
      set_absolute_position(SCREEN_W / 2, SCREEN_H / 2)
      calibrated = True
      print(
          f"[CALIBRATED] Neutral set -> X: {center_x:.3f}, Y: {center_y:.3f}"
      )
      if key == ord("o"):
        MOUTH_OPEN_THRESHOLD = 0.150


    if calibrated:
      # --- CURSOR MOVEMENT ---
      dx = anchor_point.x - center_x
      dy = anchor_point.y - center_y

      target_x = (SCREEN_W / 2) + (dx / deadzone_scale) * (SCREEN_W / 2)
      target_y = (SCREEN_H / 2) + (dy / deadzone_scale) * (SCREEN_H / 2)

      target_x = max(0, min(SCREEN_W - 1, target_x))
      target_y = max(0, min(SCREEN_H - 1, target_y))

      # Apply 1 Euro Filter
      smooth_x = filter_x.filter(now, target_x)
      smooth_y = filter_y.filter(now, target_y)

      set_absolute_position(smooth_x, smooth_y)

      # --- MOUTH CLICK LOGIC ---
      if mouth_distance > MOUTH_OPEN_THRESHOLD:
        if not is_mouth_open:
          is_mouth_open = True
          trigger_click(True)
          print("[CLICK] Mouth Opened -> Left Mouse Down")
      else:
        if is_mouth_open:
          is_mouth_open = False
          trigger_click(False)
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

  cv2.imshow("Nutshell Arch Wayland Prototype", frame)

  if key == ord("q"):
    break

cam.release()
cv2.destroyAllWindows()
landmarker.close()
ui.close()
