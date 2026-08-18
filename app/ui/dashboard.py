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
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        layout.addWidget(self.dot)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        self.status_label = QLabel(status)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        layout.addWidget(self.status_label)

    def set_status(self, status, color="#10B981"):
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px;")

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
        self.camera_feed_label = QLabel()
        self.camera_feed_label.setAlignment(Qt.AlignCenter)
        self.camera_feed_label.setStyleSheet("background-color: #0B0B14; border-radius: 8px;")
        self.camera_feed_label.setMinimumHeight(300)
        
        # Overlay for live indicator
        self.live_label = QLabel("● INACTIVE", self.camera_feed_label)
        self.live_label.setStyleSheet("color: #9CA3AF; font-weight: bold; font-size: 10px; background: transparent;")
        self.live_label.move(10, 10)
        
        self.layout.addWidget(self.camera_feed_label)
        
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
        
        self.btn_voice = self.create_btn("Start Voice", "Listening", "#2E1A47", "#8B5CF6")
        self.btn_calibrate = self.create_btn("Calibrate", "Adjust system", "#1A2E47", "#3B82F6")
        self.btn_start = self.create_btn("Start", "All Systems", "#10472D", "#10B981")
        self.btn_pause = self.create_btn("Pause", "All Systems", "#472A1A", "#F59E0B")
        
        layout.addWidget(self.btn_voice)
        layout.addWidget(self.btn_calibrate)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_pause)
        
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
        
        self.hands_free_card = HandsFreeCard()
        self.quick_actions_card = QuickActionsCard()
        left_layout.addWidget(self.hands_free_card)
        left_layout.addWidget(self.quick_actions_card)
        
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
        
        self.voice_card = CardWidget("Voice Center")
        self.voice_command_lbl = QLabel("Recognized Command\nNone")
        self.voice_command_lbl.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        self.voice_card.layout.addWidget(self.voice_command_lbl)
        vbtn = QPushButton("▶ Execute")
        vbtn.setStyleSheet("background-color: #10B981; color: white; padding: 8px; border-radius: 6px;")
        self.voice_card.layout.addWidget(vbtn)
        bottom_row.addWidget(self.voice_card)
        
        left_layout.addLayout(bottom_row)
        
        # Right column (smaller)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        
        status_card = CardWidget("System Status")
        self.status_camera = SystemStatusIndicator("Camera", "Inactive", "#9CA3AF")
        self.status_head = SystemStatusIndicator("Head Tracking", "Inactive", "#9CA3AF")
        self.status_voice = SystemStatusIndicator("Voice Recognition", "Inactive", "#9CA3AF")
        
        status_card.layout.addWidget(self.status_camera)
        status_card.layout.addWidget(self.status_head)
        status_card.layout.addWidget(self.status_voice)
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
