from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QColor

class TextOptionsWidget(QWidget):
    """Bola flotante / panel de opciones para la edición de texto in-place"""
    
    font_size_changed = pyqtSignal(int)  # delta: +1 o -1
    color_changed = pyqtSignal(QColor)
    moved = pyqtSignal(QPoint) # delta
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Estilo base para botones
        self.btn_style = """
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #666666;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """
        
        # Botones de tamaño
        self.btn_down = QPushButton("-")
        self.btn_down.setFixedSize(24, 24)
        self.btn_down.setStyleSheet(self.btn_style)
        self.btn_down.clicked.connect(lambda: self.font_size_changed.emit(-2))
        layout.addWidget(self.btn_down)
        
        self.btn_up = QPushButton("+")
        self.btn_up.setFixedSize(24, 24)
        self.btn_up.setStyleSheet(self.btn_style)
        self.btn_up.clicked.connect(lambda: self.font_size_changed.emit(2))
        layout.addWidget(self.btn_up)
        
        # Separador visual simple
        layout.addSpacing(5)
        
        # Botones de color (5 opciones)
        colors = [
            Qt.GlobalColor.red,
            Qt.GlobalColor.yellow,
            Qt.GlobalColor.cyan,
            Qt.GlobalColor.white,
            Qt.GlobalColor.black
        ]
        
        for color in colors:
            btn_color = QPushButton()
            btn_color.setFixedSize(20, 20)
            qcolor = QColor(color)
            # Borde adaptativo para blanco/negro
            border_color = "#888888" if qcolor.lightness() > 200 else "#ffffff"
            btn_color.setStyleSheet(f"""
                QPushButton {{
                    background-color: {qcolor.name()};
                    border-radius: 10px;
                    border: 2px solid {border_color};
                }}
                QPushButton:hover {{
                    border: 2px solid #00aaff;
                }}
            """)
            btn_color.clicked.connect(lambda checked, c=qcolor: self.color_changed.emit(c))
            layout.addWidget(btn_color)
            
        layout.addSpacing(5)
        
        # Botón de mover (Grip)
        self.btn_move = QPushButton("✥")
        self.btn_move.setFixedSize(24, 24)
        self.btn_move.setStyleSheet(self.btn_style + "QPushButton { font-size: 18px; }")
        self.btn_move.setToolTip("Arrastrar para mover el texto")
        self.btn_move.setCursor(Qt.CursorShape.SizeAllCursor)
        layout.addWidget(self.btn_move)
        
        # Lógica de arrastre para el botón de mover
        self.btn_move.installEventFilter(self)
        self.is_moving = False
        self.drag_start_pos = QPoint()

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 18px;
                border: 1px solid #555555;
            }
        """)
        
        self.adjustSize()

    def eventFilter(self, source, event):
        if source == self.btn_move:
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.is_moving = True
                    self.drag_start_pos = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self.is_moving:
                    current_pos = event.globalPosition().toPoint()
                    delta = current_pos - self.drag_start_pos
                    self.moved.emit(delta)
                    self.drag_start_pos = current_pos
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.is_moving:
                    self.is_moving = False
                    return True
        return super().eventFilter(source, event)

    def update_position(self, target_rect):
        """Posiciona el widget arriba del área de texto"""
        # Intentar ponerlo arriba del centro del rectángulo
        x = target_rect.center().x() - self.width() // 2
        y = target_rect.top() - self.height() - 10
        
        # Asegurarse de que no se salga de la pantalla (limites básicos)
        x = max(10, x)
        y = max(10, y)
        
        self.move(int(x), int(y))
