from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton, QTextEdit, QColorDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class TextDialog(QDialog):
    """Dialog for configuring text properties"""
    
    def __init__(self, parent=None, initial_color=Qt.GlobalColor.black):
        super().__init__(parent)
        self.setWindowTitle("Configurar Texto")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.resize(400, 300)
        
        # Store the selected color
        self.text_color = QColor(initial_color)
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Text input area
        text_label = QLabel("Texto:")
        layout.addWidget(text_label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Ingrese el texto aquí...")
        layout.addWidget(self.text_edit)
        
        # Font size selection
        font_layout = QHBoxLayout()
        font_label = QLabel("Tamaño de fuente:")
        font_layout.addWidget(font_label)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(8)
        self.font_size_spin.setMaximum(200)
        self.font_size_spin.setValue(16)
        self.font_size_spin.setSuffix(" px")
        font_layout.addWidget(self.font_size_spin)
        font_layout.addStretch()
        
        layout.addLayout(font_layout)
        
        # Color selection
        color_layout = QHBoxLayout()
        color_label = QLabel("Color del texto:")
        color_layout.addWidget(color_label)
        
        self.color_button = QPushButton("Elegir Color")
        self.color_button.clicked.connect(self._choose_color)
        self._update_color_button()
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        
        layout.addLayout(color_layout)
        
        # Buttons (OK/Cancel)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("Aceptar")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QPushButton {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
    
    def _choose_color(self):
        """Open color picker dialog"""
        color = QColorDialog.getColor(self.text_color, self, "Seleccionar Color del Texto")
        if color.isValid():
            self.text_color = color
            self._update_color_button()
    
    def _update_color_button(self):
        """Update the color button to show the selected color"""
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.text_color.name()};
                color: {"white" if self.text_color.lightness() < 128 else "black"};
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                border: 2px solid #888888;
            }}
        """)
    
    def get_text(self):
        """Return the entered text"""
        return self.text_edit.toPlainText()
    
    def get_font_size(self):
        """Return the selected font size"""
        return self.font_size_spin.value()
    
    def get_color(self):
        """Return the selected color"""
        return self.text_color
