import sounddevice as sd
import queue
import json
import sys
from vosk import Model, KaldiRecognizer

VOSK_MODEL_DIR = "/home/aniruddh_sen/Documents/VSC/PYthon/face-cursor-wayland/models/vosk-model-small-en-in-0.4/"
SAMPLE_RATE = 16000

audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

try:
    model = Model(VOSK_MODEL_DIR)
except Exception as e:
    print(f"[ERROR] Load Vosk fail: {e}", file=sys.stderr)
    sys.exit(1)

recognizer = KaldiRecognizer(model, SAMPLE_RATE)

print("[INFO] Voice module active. Listening.")

try:
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback
    ):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                res = json.loads(recognizer.Result())
                text = res.get("text", "")
                if text:
                    print(f"[COMMAND] {text}")
except KeyboardInterrupt:
    print("\n[INFO] Exit voice module.")
    sys.exit(0)
