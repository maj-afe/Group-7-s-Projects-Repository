import sys, os, time
sys.path.insert(0, os.getcwd())
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from app.voice.speech_recognition import SpeechRecognitionThread

app = QCoreApplication.instance() or QCoreApplication([])

t = SpeechRecognitionThread()
captured = {"status": [], "err": []}
t.status_update.connect(lambda s: captured["status"].append(s))
t.error_occurred.connect(lambda e: captured["err"].append(e))

t.start()

# Pump events until the thread finishes or 3s elapse.
deadline = time.time() + 3
while t.isRunning() and time.time() < deadline:
    app.processEvents(QEventLoop.AllEvents, 50)

t.wait(1000)
print("statuses =", captured["status"])
print("errors   =", captured["err"][:1])
print("OK: graceful failure with no whisper binary installed")
