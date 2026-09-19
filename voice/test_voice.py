import sys

from PySide6.QtWidgets import QApplication

from .voice_assist import VoiceAssistant


def main():

    app = QApplication(sys.argv)

    voice = VoiceAssistant()

    voice.status_changed.connect(
        lambda status:
            print(
                f"[STATUS] {status}"
            )
    )

    voice.command_executed.connect(
        lambda text, command:
            print(
                f"[COMMAND] {text} -> {command}"
            )
    )

    voice.error_occurred.connect(
        lambda error:
            print(
                f"[ERROR] {error}"
            )
    )

    voice.start()

    exit_code = app.exec()

    voice.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()