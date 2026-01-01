"""
Key Capture Dialog
Small dialog to capture a single key press for shortcut configuration
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

class KeyCaptureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.captured_key = None
        self.captured_key_name = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Capturar Atajo")
        self.setModal(True)
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        # Instruction label
        self.instruction_label = QLabel("Presiona una tecla para usar como atajo...")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setStyleSheet("font-size: 12pt; padding: 20px;")
        layout.addWidget(self.instruction_label)
        
        # Key display label
        self.key_label = QLabel("")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1a73e8; padding: 10px;")
        layout.addWidget(self.key_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.accept_button = QPushButton("Aceptar")
        self.accept_button.clicked.connect(self.accept)
        self.accept_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Capture the key press"""
        # Ignore modifier-only keys like Shift, Ctrl, Alt when pressed alone
        # But allow them if they're the actual key we want
        key = event.key()
        
        # Get the key name
        key_name = self._get_key_name(key, event)
        
        if key_name:
            self.captured_key = key
            self.captured_key_name = key_name
            self.key_label.setText(f"Tecla: {key_name}")
            self.accept_button.setEnabled(True)
        
        event.accept()
    
    def _get_key_name(self, key, event):
        """Convert key code to readable name"""
        # Special  keys
        special_keys = {
            Qt.Key.Key_Shift: "Shift",
            Qt.Key.Key_Control: "Ctrl",
            Qt.Key.Key_Alt: "Alt",
            Qt.Key.Key_Meta: "Meta",
            Qt.Key.Key_Space: "Espacio",
            Qt.Key.Key_Return: "Enter",
            Qt.Key.Key_Enter: "Enter",
            Qt.Key.Key_Backspace: "Backspace",
            Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Escape: "Esc",
            Qt.Key.Key_Delete: "Supr",
            Qt.Key.Key_Insert: "Insert",
            Qt.Key.Key_Home: "Inicio",
            Qt.Key.Key_End: "Fin",
            Qt.Key.Key_PageUp: "Re Pág",
            Qt.Key.Key_PageDown: "Av Pág",
            Qt.Key.Key_Up: "Flecha Arriba",
            Qt.Key.Key_Down: "Flecha Abajo",
            Qt.Key.Key_Left: "Flecha Izquierda",
            Qt.Key.Key_Right: "Flecha Derecha",
        }
        
        if key in special_keys:
            return special_keys[key]
        
        # Function keys
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
            f_num = key - Qt.Key.Key_F1 + 1
            return f"F{f_num}"
        
        # Regular keys - use the text
        text = event.text().upper()
        if text and text.isprintable():
            return text
        
        # Try to get key sequence string
        return None
    
    def get_captured_key(self):
        """Return the captured key code and name"""
        return self.captured_key, self.captured_key_name
