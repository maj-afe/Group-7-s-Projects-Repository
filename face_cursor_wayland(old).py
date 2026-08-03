import subprocess
import cv2
import mediapipe as mp

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.7
)

# Since pyautogui fails on Wayland, we fetch screen resolution via a lightweight check or hardcode your display resolution (e.g., 1920, 1080)
# Change these to match your actual monitor resolution:
screen_w, screen_h = 1280 , 720

cam = cv2.VideoCapture(0)

# Calibration and smoothing variables
calibrated = False
center_x, center_y = 0.5, 0.5
deadzone_scale = 0.12

smooth_x, smooth_y = screen_w / 2, screen_h / 2
alpha = 0.25  # Lower = smoother, Higher = faster/snappier

print(
    "[INFO] Wayland Session Active. Look straight at your screen and press 'C'"
    " to calibrate."
)


def move_cursor_wayland(x, y):
  """Sends absolute mouse position commands via ydotool on Wayland"""
  try:
    # ydotool mousemove command syntax: ydotool mousemove -x <x> -y <y> (absolute positioning)
    subprocess.run(
        ["ydotool", "mousemove", "-x", str(int(x)), "-y", str(int(y))],
        check=False,
    )
  except Exception as e:
    pass


while cam.isOpened():
  success, frame = cam.read()
  if not success:
    break

  frame = cv2.flip(frame, 1)
  h, w, _ = frame.shape
  rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
  results = face_mesh.process(rgb_frame)

  key = cv2.waitKey(1) & 0xFF

  if results.multi_face_landmarks:
    landmarks = results.multi_face_landmarks[0].landmark
    anchor_point = landmarks[168]  # Bridge of the nose anchor

    # Recalibrate neutral stance on 'c'
    if key == ord("c"):
      center_x, center_y = anchor_point.x, anchor_point.y
      calibrated = True
      print(
          f"[CALIBRATED] Neutral set -> X: {center_x:.2f}, Y:"
          f" {center_y:.2f}"
      )

    if calibrated:
      dx = anchor_point.x - center_x
      dy = anchor_point.y - center_y

      target_x = screen_w / 2 + (dx / deadzone_scale) * (screen_w / 2)
      target_y = screen_h / 2 + (dy / deadzone_scale) * (screen_h / 2)

      target_x = max(0, min(screen_w - 1, target_x))
      target_y = max(0, min(screen_h - 1, target_y))

      # Exponential Moving Average filter for smooth tracking
      smooth_x = alpha * target_x + (1 - alpha) * smooth_x
      smooth_y = alpha * target_y + (1 - alpha) * smooth_y

      # Move cursor natively on Wayland
      move_cursor_wayland(smooth_x, smooth_y)

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
