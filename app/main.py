import sys
import os

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():

    # ==========================================
    # CREATE QT APPLICATION
    # ==========================================

    app = QApplication(sys.argv)

    # Default font
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    # ==========================================
    # MAIN WINDOW
    # ==========================================

    window = MainWindow()

    window.show()

    # ==========================================
    # EVENT LOOP
    # ==========================================

    sys.exit(app.exec())


if __name__ == "__main__":
    main()