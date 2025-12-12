from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

class FloatingMenu(QWidget):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(50) # Fixed width, variable height
        
        # Position variables for dragging
        self.dragging = False
        self.offset = QPoint()

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Main Menu Button
        self.button = QPushButton("☰")
        self.button.setFixedSize(50, 50)
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 25px;
                font-size: 24px;
                border: 2px solid #555555;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        self.button.clicked.connect(self.clicked.emit)
        layout.addWidget(self.button)

        # Drag Handle (Hidden by default)
        self.handle = QLabel("✥")
        self.handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.handle.setFixedSize(50, 20)
        self.handle.setStyleSheet("""
            QLabel {
                background-color: #222222;
                color: #aaaaaa;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                font-size: 14px;
            }
            QLabel:hover {
                background-color: #333333;
                color: white;
            }
        """)
        self.handle.hide()
        layout.addWidget(self.handle)

    def enterEvent(self, event):
        self.handle.show()
        self.adjustSize()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.handle.hide()
        self.adjustSize()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        # Only allow dragging if clicking on the handle area or if the handle is visible and below button?
        # Simplest: If handle is visible, check if we clicked on it?
        # Or just allow dragging the whole widget if we aren't clicking the button.
        # But user asked to use the symbol to move it.
        # Let's check if the press is within the handle's geometry relative to the widget.
        
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child == self.handle:
                self.dragging = True
                self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

class Toolbar(QWidget):
    toggle_overlay = pyqtSignal()
    hide_toolbar = pyqtSignal()
    close_app = pyqtSignal()
    # New signals for tools
    tool_pen = pyqtSignal()
    tool_eraser = pyqtSignal()
    tool_clear = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dragging state
        self.dragging = False
        self.offset = QPoint()
        
        layout = QHBoxLayout()
        # Add some margin so there's space to grab if needed, or tight pack with handle
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # Style for buttons
        btn_style = """
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """

        # Drag Handle (Grip)
        self.label_grip = QLabel("✥")
        self.label_grip.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 5px;
                background-color: #222222;
                border-radius: 5px;
            }
            QLabel:hover {
                background-color: #333333;
                color: white;
            }
        """)
        self.label_grip.setToolTip("Arrastrar para mover")
        layout.addWidget(self.label_grip)

        # Hide Toolbar Button (Moved here)
        self.btn_hide = QPushButton("⬇️")
        self.btn_hide.setToolTip("Ocultar Barra")
        self.btn_hide.setStyleSheet(btn_style)
        self.btn_hide.clicked.connect(self.hide_toolbar.emit)
        layout.addWidget(self.btn_hide)

        # Toggle Overlay Button
        self.btn_toggle = QPushButton("👁️")
        self.btn_toggle.setToolTip("Mostrar/Ocultar Overlay")
        self.btn_toggle.setStyleSheet(btn_style)
        self.btn_toggle.clicked.connect(self.toggle_overlay.emit)
        layout.addWidget(self.btn_toggle)

        # Pen Button
        self.btn_pen = QPushButton("✏️")
        self.btn_pen.setToolTip("Lápiz")
        self.btn_pen.setStyleSheet(btn_style)
        self.btn_pen.clicked.connect(self.tool_pen.emit)
        layout.addWidget(self.btn_pen)

        # Eraser Button
        self.btn_eraser = QPushButton("🧹")
        self.btn_eraser.setToolTip("Borrador")
        self.btn_eraser.setStyleSheet(btn_style)
        self.btn_eraser.clicked.connect(self.tool_eraser.emit)
        layout.addWidget(self.btn_eraser)

        # Clear All Button
        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setToolTip("Limpiar Todo")
        self.btn_clear.setStyleSheet(btn_style)
        self.btn_clear.clicked.connect(self.tool_clear.emit)
        layout.addWidget(self.btn_clear)

        # Close App Button
        self.btn_close = QPushButton("❌")
        self.btn_close.setToolTip("Cerrar Programa")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: 1px solid #990000;
                border-radius: 5px;
                padding: 5px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        self.btn_close.clicked.connect(self.close_app.emit)
        layout.addWidget(self.btn_close)

    def set_layout_rtl(self, is_rtl):
        direction = QBoxLayout.Direction.RightToLeft if is_rtl else QBoxLayout.Direction.LeftToRight
        self.layout().setDirection(direction)
        # Force re-layout/update
        self.layout().update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False
