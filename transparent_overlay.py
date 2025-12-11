import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt

class TransparentOverlay(QWidget):
    def __init__(self):
        super().__init__()
        
        # Configurar la ventana para que no tenga bordes y esté siempre encima
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Hacer el fondo de la ventana transparente
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Cubrir toda la pantalla
        self.showFullScreen()
        
        # Configurar el layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Crear el botón de cerrar
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.setFixedSize(100, 40)
        self.close_btn.clicked.connect(self.close)
        
        # Estilo para asegurar que el botón sea visible
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        
        # Colocar el botón en la esquina superior derecha
        layout.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.show()
    sys.exit(app.exec())
