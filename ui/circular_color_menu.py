import math
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen

class CircularColorMenu(QWidget):
    """Menú circular de selección rápida de colores"""
    
    color_selected = pyqtSignal(QColor)
    advanced_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.radius = 60  # Radio del círculo
        self.button_size = 32
        
        # Colores por defecto (Rojo, Amarillo, Cian, Blanco, Negro)
        self.colors = [
            Qt.GlobalColor.red,
            Qt.GlobalColor.yellow,
            Qt.GlobalColor.cyan,
            Qt.GlobalColor.white,
            Qt.GlobalColor.black
        ]
        
        self.buttons = []
        
        # Crear botones de color
        for color in self.colors:
            btn = QPushButton(self)
            btn.setFixedSize(self.button_size, self.button_size)
            qcolor = QColor(color)
            border_color = "#888888" if qcolor.lightness() > 200 else "#ffffff"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {qcolor.name()};
                    border-radius: {self.button_size // 2}px;
                    border: 2px solid {border_color};
                }}
                QPushButton:hover {{
                    border: 3px solid #00aaff;
                }}
            """)
            btn.clicked.connect(lambda checked, c=qcolor: self._on_color_picked(c))
            self.buttons.append(btn)
            
        # Botón avanzado (engranaje o más)
        self.btn_advanced = QPushButton("⚙️", self)
        self.btn_advanced.setFixedSize(self.button_size, self.button_size)
        self.btn_advanced.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                border-radius: {self.button_size // 2}px;
                border: 2px solid #ffffff;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: #666666;
            }}
        """)
        self.btn_advanced.clicked.connect(self._on_advanced_clicked)
        self.buttons.append(self.btn_advanced)
        
        # Tamaño total del widget
        total_size = (self.radius + self.button_size) * 2
        self.setFixedSize(total_size, total_size)
        
        self._position_buttons()

    def _position_buttons(self):
        center = self.width() // 2
        n = len(self.buttons)
        for i, btn in enumerate(self.buttons):
            # Calcular ángulo (repartir en el círculo)
            angle = (i * 2 * math.pi / n) - (math.pi / 2) # Empezar arriba
            x = center + self.radius * math.cos(angle) - btn.width() // 2
            y = center + self.radius * math.sin(angle) - btn.height() // 2
            btn.move(int(x), int(y))

    def _on_color_picked(self, color):
        self.color_selected.emit(color)
        self.close()

    def _on_advanced_clicked(self):
        self.advanced_clicked.emit()
        self.close()

    def show_at(self, pos):
        # Centrar el widget en el puntero
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)
        self.show()

    def paintEvent(self, event):
        # Dibujar un fondo sutil opcional (como una sombra circular)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
        painter.setPen(Qt.PenStyle.NoPen)
        center = self.width() // 2
        painter.drawEllipse(QPoint(center, center), self.radius + 10, self.radius + 10)
