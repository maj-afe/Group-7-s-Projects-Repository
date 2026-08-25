# build.ps1
Write-Host "Installing PyInstaller and build tools..."
pip install pyinstaller pyinstaller-hooks-contrib

Write-Host "Building standalone .exe for BUG Dashboard..."
pyinstaller --noconfirm --onefile --windowed `
    --name "BUG_Dashboard" `
    --paths . `
    --collect-all mediapipe `
    --collect-all faster_whisper `
    --collect-all silero_vad `
    --hidden-import "PySide6.QtCore" `
    --hidden-import "PySide6.QtGui" `
    --hidden-import "PySide6.QtWidgets" `
    --hidden-import "sounddevice" `
    --hidden-import "numpy" `
    --hidden-import "torch" `
    --hidden-import "cv2" `
    --clean `
    app/main.py

Write-Host "Build complete! The executable is located in the 'dist' folder."
