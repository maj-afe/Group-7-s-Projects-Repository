import sounddevice as sd
import queue
import json
import sys
import os
from vosk import Model, KaldiRecognizer
from PySide6.QtCore import QThread, Signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VOSK_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "models", "vosk-model-small-en-in-0.4")
SAMPLE_RATE = 16000

class VoiceThread(QThread):
    command_recognized = Signal(str)
    status_update = Signal(str)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.audio_queue = queue.Queue()
        self.is_running = True

    def audio_callback(self, indata, frames, time, status):
        if status:
            pass # ignore minor status prints to avoid console spam
        if self.is_running:
            self.audio_queue.put(bytes(indata))

    def run(self):
        self.status_update.emit("Initializing...")
        if not os.path.exists(VOSK_MODEL_DIR):
            self.error_occurred.emit(f"Vosk model directory not found at: {VOSK_MODEL_DIR}")
            return

        try:
            model = Model(VOSK_MODEL_DIR)
        except Exception as e:
            self.error_occurred.emit(f"Load Vosk fail: {e}")
            return

        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        self.status_update.emit("Listening")

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self.audio_callback
            ):
                while self.is_running:
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                        if recognizer.AcceptWaveform(data):
                            res = json.loads(recognizer.Result())
                            text = res.get("text", "")
                            if text:
                                self.command_recognized.emit(text)
                    except queue.Empty:
                        continue
        except sd.PortAudioError as e:
            self.error_occurred.emit(f"Could not open audio input stream: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error in voice module: {e}")
        finally:
            self.status_update.emit("Inactive")

    def stop(self):
        self.is_running = False
        self.wait()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    thread = VoiceThread()
    thread.command_recognized.connect(lambda cmd: print(f"Command: {cmd}"))
    thread.status_update.connect(lambda st: print(f"Status: {st}"))
    thread.error_occurred.connect(lambda e: print(f"Error: {e}"))
    thread.start()
    sys.exit(app.exec())
