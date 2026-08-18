import json
import os
import queue

import sounddevice as sd
from vosk import Model, KaldiRecognizer
from PySide6.QtCore import QThread, Signal


class SpeechRecognitionThread(QThread):

    command_recognized = Signal(str)
    status_update = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, model_path=None):
        super().__init__()

        self.audio_queue = queue.Queue()
        self.running = False
        self.sample_rate = 16000

        self.model_path = model_path or self.find_model()

    def find_model(self):

        # Project root:
        # Group-7-s-Projects-Repository

        project_root = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                ".."
            )
        )

        models_dir = os.path.join(
            project_root,
            "models"
        )

        preferred = os.path.join(
            models_dir,
            "vosk-model-small-en-in-0.4"
        )

        if os.path.isdir(preferred):
            return preferred

        return preferred

    def audio_callback(
        self,
        indata,
        frames,
        time,
        status
    ):

        if status:
            print("[Voice Audio]", status)

        if self.running:
            self.audio_queue.put(bytes(indata))

    def run(self):

        self.running = True

        self.status_update.emit(
            "Loading offline voice model..."
        )

        if not os.path.isdir(self.model_path):

            self.error_occurred.emit(
                "Vosk model not found:\n"
                + self.model_path
            )

            self.running = False
            return

        try:

            print(
                "[Voice] Loading model:",
                self.model_path
            )

            model = Model(self.model_path)

            recognizer = KaldiRecognizer(
                model,
                self.sample_rate
            )

        except Exception as e:

            self.error_occurred.emit(
                f"Failed to load Vosk model:\n{e}"
            )

            self.running = False
            return

        self.status_update.emit("Listening")

        try:

            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self.audio_callback
            ):

                while self.running:

                    try:

                        data = self.audio_queue.get(
                            timeout=0.1
                        )

                    except queue.Empty:

                        continue

                    if recognizer.AcceptWaveform(data):

                        result = json.loads(
                            recognizer.Result()
                        )

                        text = result.get(
                            "text",
                            ""
                        ).strip()

                        if text:

                            print(
                                "[Voice] Recognized:",
                                text
                            )

                            self.command_recognized.emit(
                                text
                            )

        except sd.PortAudioError as e:

            self.error_occurred.emit(
                f"Microphone error:\n{e}"
            )

        except Exception as e:

            self.error_occurred.emit(
                f"Voice recognition error:\n{e}"
            )

        finally:

            self.running = False

            self.status_update.emit(
                "Inactive"
            )

    def stop(self):

        self.running = False

        if self.isRunning():
            self.wait(2000)