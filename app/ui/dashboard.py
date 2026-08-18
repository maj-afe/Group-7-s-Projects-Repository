from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QGridLayout, QPushButton, QFrame, QScrollArea, QProgressBar, QLineEdit)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPalette, QFont

class CardWidget(QFrame):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("CardWidget")
        self.setStyleSheet("""
            #CardWidget {
                background-color: #13131F;
                border-radius: 12px;
                border: 1px solid #1F1F33;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        
        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14px;")
            self.layout.addWidget(self.title_label)

class SystemStatusIndicator(QWidget):
    def __init__(self, name, status, color="#10B981"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        layout.addWidget(dot)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        status_label = QLabel(status)
        status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        layout.addWidget(status_label)

class HandsFreeCard(CardWidget):
    def __init__(self):
        super().__init__()
        
        header_layout = QHBoxLayout()
        title = QLabel("Hands-Free Mode")
        title.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 16px;")
        subtitle = QLabel("All core systems are running")
        subtitle.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        
        title_vlayout = QVBoxLayout()
        title_vlayout.addWidget(title)
        title_vlayout.addWidget(subtitle)
        header_layout.addLayout(title_vlayout)
        header_layout.addStretch()
        
        self.layout.addLayout(header_layout)
        
        # Camera Feed Mockup
        camera_frame = QFrame()
        camera_frame.setStyleSheet("""
            background-color: #0B0B14;
            border-radius: 8px;
        """)
        camera_frame.setMinimumHeight(200)
        camera_layout = QVBoxLayout(camera_frame)
        
        live_label = QLabel("● LIVE")
        live_label.setStyleSheet("color: #10B981; font-weight: bold; font-size: 10px;")
        camera_layout.addWidget(live_label, alignment=Qt.AlignRight | Qt.AlignTop)
        camera_layout.addStretch()
        
        self.layout.addWidget(camera_frame)
        
        # Status indicators bottom
        status_hlayout = QHBoxLayout()
        for text, status, color in [("Camera", "Active", "#10B981"), ("Face Detected", "Detected", "#10B981"), 
                                    ("Head Tracking", "Tracking", "#10B981"), ("Voice Recognition", "Listening", "#10B981")]:
            vlayout = QVBoxLayout()
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
            stat = QLabel(status)
            stat.setStyleSheet(f"color: {color}; font-size: 12px;")
            vlayout.addWidget(lbl, alignment=Qt.AlignCenter)
            vlayout.addWidget(stat, alignment=Qt.AlignCenter)
            status_hlayout.addLayout(vlayout)
            
        self.layout.addLayout(status_hlayout)

class QuickActionsCard(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        btn1 = self.create_btn("Start Voice", "Listening", "#2E1A47", "#8B5CF6")
        btn2 = self.create_btn("Calibrate", "Adjust system", "#1A2E47", "#3B82F6")
        btn3 = self.create_btn("Start", "All Systems", "#10472D", "#10B981")
        btn4 = self.create_btn("Pause", "All Systems", "#472A1A", "#F59E0B")
        
        layout.addWidget(btn1)
        layout.addWidget(btn2)
        layout.addWidget(btn3)
        layout.addWidget(btn4)
        
    def create_btn(self, title, subtitle, bg_color, accent):
        btn = QPushButton()
        btn.setMinimumHeight(60)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {accent};
                border-radius: 8px;
                text-align: left;
                padding: 10px;
            }}
            QPushButton:hover {{ background-color: {accent}; }}
        """)
        # We need a custom layout inside the button to show title + subtitle
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(10, 5, 10, 5)
        t = QLabel(title)
        t.setStyleSheet(f"color: #FFFFFF; font-weight: bold; background: transparent; border: none;")
        s = QLabel(subtitle)
        s.setStyleSheet(f"color: #D1D5DB; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(t)
        layout.addWidget(s)
        return btn

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0B0B14;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        greeting_layout = QVBoxLayout()
        greeting = QLabel("Good afternoon, User! 👋")
        greeting.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: bold;")
        subgreeting = QLabel("Let's make browsing easier and smarter.")
        subgreeting.setStyleSheet("color: #9CA3AF; font-size: 14px;")
        greeting_layout.addWidget(greeting)
        greeting_layout.addWidget(subgreeting)
        
        sys_active = QLabel("● System Active\nAll systems normal")
        sys_active.setStyleSheet("color: #10B981; background-color: #13131F; border-radius: 8px; padding: 10px; border: 1px solid #1F1F33;")
        sys_active.setAlignment(Qt.AlignRight)
        
        header_layout.addLayout(greeting_layout)
        header_layout.addStretch()
        header_layout.addWidget(sys_active)
        main_layout.addLayout(header_layout)
        
        # Main Grid Layout
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Left column (larger)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        
        left_layout.addWidget(HandsFreeCard())
        left_layout.addWidget(QuickActionsCard())
        
        # Bottom row in left column (My Study, AI Assistant, Voice Center)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(20)
        
        # My Study Mini Card
        study_card = CardWidget("My Study")
        study_lbl = QLabel("Continue Reading\nArtificial Intelligence - History section")
        study_lbl.setStyleSheet("color: #FFFFFF;")
        study_card.layout.addWidget(study_lbl)
        btn = QPushButton("▶ Continue Reading")
        btn.setStyleSheet("background-color: #6D28D9; color: white; padding: 8px; border-radius: 6px;")
        study_card.layout.addWidget(btn)
        bottom_row.addWidget(study_card)
        
        # AI Assistant Mini Card
        ai_card = CardWidget("AI Assistant")
        ai_lbl = QLabel("Current Page\nArtificial Intelligence (en.wikipedia.org)")
        ai_lbl.setStyleSheet("color: #FFFFFF;")
        ai_card.layout.addWidget(ai_lbl)
        inp = QLineEdit()
        inp.setPlaceholderText("Ask anything about this page...")
        inp.setStyleSheet("background-color: #1F1F33; color: white; border-radius: 6px; padding: 6px;")
        ai_card.layout.addWidget(inp)
        bottom_row.addWidget(ai_card)
        
        # Voice Center Mini Card
        voice_card = CardWidget("Voice Center")
        v_lbl = QLabel("Recognized Command\nScroll down")
        v_lbl.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        voice_card.layout.addWidget(v_lbl)
        vbtn = QPushButton("▶ Execute")
        vbtn.setStyleSheet("background-color: #10B981; color: white; padding: 8px; border-radius: 6px;")
        voice_card.layout.addWidget(vbtn)
        bottom_row.addWidget(voice_card)
        
        left_layout.addLayout(bottom_row)
        
        # Right column (smaller)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        
        status_card = CardWidget("System Status")
        status_card.layout.addWidget(SystemStatusIndicator("Camera", "Active"))
        status_card.layout.addWidget(SystemStatusIndicator("Head Tracking", "Active"))
        status_card.layout.addWidget(SystemStatusIndicator("Voice Recognition", "Active"))
        status_card.layout.addWidget(SystemStatusIndicator("Internet", "Connected"))
        right_layout.addWidget(status_card)
        
        history_card = CardWidget("Activity History")
        h_lbl1 = QLabel("Wikipedia\nArtificial Intelligence (55%)")
        h_lbl1.setStyleSheet("color: #FFFFFF;")
        history_card.layout.addWidget(h_lbl1)
        bar = QProgressBar()
        bar.setValue(55)
        bar.setTextVisible(False)
        bar.setStyleSheet("QProgressBar { background-color: #1F1F33; border-radius: 2px; max-height: 4px; } QProgressBar::chunk { background-color: #8B5CF6; }")
        history_card.layout.addWidget(bar)
        right_layout.addWidget(history_card)
        
        right_layout.addStretch()
        
        # Add to grid
        grid.addLayout(left_layout, 0, 0, 1, 3)
        grid.addLayout(right_layout, 0, 3, 1, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(3, 1)
        
        main_layout.addLayout(grid)
