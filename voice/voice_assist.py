from PySide6.QtCore import QObject, Signal

from .speech_recognition import SpeechRecognitionThread
from .command_handler import CommandHandler


class VoiceAssistant(QObject):

    command_executed = Signal(str, str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self):

        super().__init__()

        self.command_handler = CommandHandler()

        self.recognition_thread = None

        self.running = False

    # =====================================================
    # START VOICE
    # =====================================================

    def start(self):

        if self.running:
            return

        print("[VoiceAssistant] Starting...")

        self.recognition_thread = (
            SpeechRecognitionThread()
        )

        self.recognition_thread.command_recognized.connect(
            self.handle_command
        )

        self.recognition_thread.status_update.connect(
            self.handle_status
        )

        self.recognition_thread.error_occurred.connect(
            self.handle_error
        )

        self.running = True

        self.recognition_thread.start()

    # =====================================================
    # STOP VOICE
    # =====================================================

    def stop(self):

        if not self.running:
            return

        print("[VoiceAssistant] Stopping...")

        self.running = False

        if self.recognition_thread:

            self.recognition_thread.stop()

            self.recognition_thread = None

        self.status_changed.emit(
            "Inactive"
        )

    # =====================================================
    # COMMAND
    # =====================================================

    def handle_command(self, text):

        print(
            f"[VoiceAssistant] Command received: {text}"
        )

        try:

            result = self.command_handler.execute(
                text
            )

            if result:

                self.command_executed.emit(
                    text,
                    result
                )

            else:

                self.command_executed.emit(
                    text,
                    "unknown"
                )

        except Exception as e:

            print(
                "[VoiceAssistant] Command error:",
                e
            )

            self.error_occurred.emit(
                str(e)
            )

    # =====================================================
    # STATUS
    # =====================================================

    def handle_status(self, status):

        print(
            f"[VoiceAssistant] Status: {status}"
        )

        self.status_changed.emit(
            status
        )

    # =====================================================
    # ERROR
    # =====================================================

    def handle_error(self, error):

        print(
            f"[VoiceAssistant] Error: {error}"
        )

        self.error_occurred.emit(
            error
        )

    # =====================================================
    # EMERGENCY STOP
    # =====================================================

    def emergency_stop(self):

        self.command_handler.enabled = False

        print(
            "[VoiceAssistant] EMERGENCY STOP"
        )

    # =====================================================
    # ENABLE AGAIN
    # =====================================================

    def enable_control(self):

        self.command_handler.reset_emergency_stop()

        print(
            "[VoiceAssistant] Control enabled"
        )

    # =====================================================
    # STATUS
    # =====================================================

    def is_active(self):

        return self.running