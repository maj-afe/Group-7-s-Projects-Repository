import sys
import os

# Add project root to Python path
if getattr(sys, 'frozen', False):
    # When frozen, __file__ is sys._MEIPASS/main.py
    # But the bundled modules are loaded from the internal PYZ archive.
    # No need to modify sys.path for internal modules, but just in case:
    project_root = sys._MEIPASS
else:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

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