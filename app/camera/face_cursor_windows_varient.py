import math
import os
import time
import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "face_landmarker.task")

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

class CameraThread(QThread):
    frame_ready = Signal(QImage)
    status_update = Signal(str)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.cursor_control_active = True
        self.SCREEN_W, self.SCREEN_H = pyautogui.size()
        
        self.calibrated = False
        self.needs_calibration = False
        self.center_x, self.center_y = 0.5, 0.5
        self.deadzone_scale = 0.12
        self.smooth_x = self.SCREEN_W / 2
        self.smooth_y = self.SCREEN_H / 2
        self.alpha = 0.25
        self.MOUTH_OPEN_THRESHOLD = 0.035
        self.is_mouth_open = False
        self.back_triggered = False

    def calibrate(self):
        self.needs_calibration = True

    def set_cursor_control(self, active: bool):
        self.cursor_control_active = active

    def run(self):
        self.status_update.emit("Initializing Camera...")
        
        if not os.path.exists(MODEL_PATH):
            self.error_occurred.emit(f"Mediapipe model not found at {MODEL_PATH}")
            return
            
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.7,
        )
        try:
            landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            self.error_occurred.emit(f"Failed to load MediaPipe model: {e}")
            return

        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            self.error_occurred.emit("Could not open camera (index 0).")
            landmarker.close()
            return

        self.status_update.emit("Active")

        while self.is_running and cam.isOpened():
            success, frame = cam.read()
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int(time.time() * 1000)
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            if results.face_landmarks:
                landmarks = results.face_landmarks[0]
                anchor_point = landmarks[168]
                upper_lip = landmarks[13]
                lower_lip = landmarks[14]

                mouth_distance = math.hypot(
                    upper_lip.x - lower_lip.x, upper_lip.y - lower_lip.y
                )

                if self.needs_calibration:
                    self.center_x, self.center_y = anchor_point.x, anchor_point.y
                    self.smooth_x = self.SCREEN_W / 2
                    self.smooth_y = self.SCREEN_H / 2
                    self.needs_calibration = False
                    self.calibrated = True

                if self.calibrated and self.cursor_control_active:
                    dx = anchor_point.x - self.center_x
                    dy = anchor_point.y - self.center_y

                    target_x = (self.SCREEN_W / 2) + (dx / self.deadzone_scale) * (self.SCREEN_W / 2)
                    target_y = (self.SCREEN_H / 2) + (dy / self.deadzone_scale) * (self.SCREEN_H / 2)

                    target_x = max(0, min(self.SCREEN_W - 1, target_x))
                    target_y = max(0, min(self.SCREEN_H - 1, target_y))

                    self.smooth_x = self.alpha * target_x + (1 - self.alpha) * self.smooth_x
                    self.smooth_y = self.alpha * target_y + (1 - self.alpha) * self.smooth_y

                    pyautogui.moveTo(int(self.smooth_x), int(self.smooth_y))

                    # Direct gesture scrolling based on vertical head movement (dy)
                    if dy < -0.04: # Looking up
                        scroll_speed = int((abs(dy) - 0.04) * 1500)
                        pyautogui.scroll(scroll_speed)
                    elif dy > 0.04: # Looking down
                        scroll_speed = int((abs(dy) - 0.04) * 1500)
                        pyautogui.scroll(-scroll_speed)

                    # Back navigation on horizontal head movement (dx)
                    if dx < -0.15 or dx > 0.15: # Head turned completely to the side
                        if not self.back_triggered:
                            pyautogui.hotkey('browserback')
                            self.back_triggered = True
                    elif abs(dx) < 0.08: # Reset trigger when head returns to center
                        self.back_triggered = False

                    if mouth_distance > self.MOUTH_OPEN_THRESHOLD:
                        if not self.is_mouth_open:
                            self.is_mouth_open = True
                            pyautogui.mouseDown(button="left")
                    else:
                        if self.is_mouth_open:
                            self.is_mouth_open = False
                            pyautogui.mouseUp(button="left")

                # Visual Feedback
                cv2.circle(rgb_frame, (int(anchor_point.x * w), int(anchor_point.y * h)), 5, (0, 255, 0), -1)
                lip_color = (255, 0, 0) if self.is_mouth_open else (0, 0, 255)
                cv2.circle(rgb_frame, (int(upper_lip.x * w), int(upper_lip.y * h)), 4, lip_color, -1)
                cv2.circle(rgb_frame, (int(lower_lip.x * w), int(lower_lip.y * h)), 4, lip_color, -1)

            # Convert to QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            self.frame_ready.emit(q_img.copy())

        cam.release()
        landmarker.close()
        self.status_update.emit("Inactive")

    def stop(self):
        self.is_running = False
        self.wait()