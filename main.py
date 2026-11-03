import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFrame

class StudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SkyRealm Mod Studio")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #0b1020; color: #edf2ff; }
            QLabel#brand { color: #f4f7ff; font-size: 38px; font-weight: 800; letter-spacing: 1px; }
            QLabel#subtitle { color: #8d9ab8; font-size: 14px; }
            QLabel#eyebrow { color: #66e3a4; font-size: 11px; font-weight: 700; letter-spacing: 3px; }
            QFrame#panel { background: #111a30; border: 1px solid #263552; border-radius: 22px; }
            QPushButton#primary { background: #35c987; color: #07150f; border: 0; border-radius: 12px; padding: 17px 34px; font-size: 17px; font-weight: 750; }
            QPushButton#primary:hover { background: #54dda0; }
            QPushButton#primary:pressed { background: #27ad73; }
            QPushButton#exit { background: transparent; color: #9aa8c4; border: 1px solid #34415d; border-radius: 10px; padding: 12px 28px; font-size: 13px; }
            QPushButton#exit:hover { background: #1b2740; color: #ffffff; }
            QLabel#footer { color: #586783; font-size: 11px; }
        """)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(54, 38, 54, 28)
        layout.setSpacing(0)
        top = QVBoxLayout()
        top.setSpacing(5)
        eyebrow = QLabel("SKYREALM • CREATOR TOOLS")
        eyebrow.setObjectName("eyebrow")
        brand = QLabel("MOD STUDIO")
        brand.setObjectName("brand")
        subtitle = QLabel("Инструмент для создания модификаций SkyRealm")
        subtitle.setObjectName("subtitle")
        top.addWidget(eyebrow)
        top.addWidget(brand)
        top.addWidget(subtitle)
        layout.addLayout(top)
        layout.addStretch(1)
        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(48, 54, 48, 54)
        panel_layout.setSpacing(18)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome = QLabel("Добро пожаловать в SkyRealm Mod Studio")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        welcome.setStyleSheet("color: #f2f6ff;")
        hint = QLabel("Создай собственную модификацию для своего мира")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #91a0bd; font-size: 13px;")
        create_button = QPushButton("＋   Создать мод")
        create_button.setObjectName("primary")
        create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        create_button.setMinimumWidth(250)
        create_button.clicked.connect(self.create_mod)
        panel_layout.addWidget(welcome)
        panel_layout.addWidget(hint)
        panel_layout.addSpacing(18)
        panel_layout.addWidget(create_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(panel, stretch=0)
        layout.addStretch(1)
        bottom = QVBoxLayout()
        bottom.setSpacing(14)
        exit_button = QPushButton("Выйти из Studio")
        exit_button.setObjectName("exit")
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(self.close)
        bottom.addWidget(exit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        footer = QLabel("SKYREALM MOD STUDIO  •  EARLY DEVELOPMENT")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.addWidget(footer)
        layout.addLayout(bottom)
        self.setCentralWidget(root)

    def create_mod(self):
        QMessageBox.information(self, "Создать мод", "Главный экран готов. Следующим этапом будет добавлен редактор создания модов.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SkyRealm Mod Studio")
    app.setStyle("Fusion")
    window = StudioWindow()
    window.show()
    sys.exit(app.exec())
