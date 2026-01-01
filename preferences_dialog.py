"""
Preferences Dialog
Main preferences window for configuring keyboard shortcuts
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
                              QHeaderView)
from PyQt6.QtCore import Qt
from key_capture_dialog import KeyCaptureDialog
from preferences_manager import PreferencesManager

class PreferencesDialog(QDialog):
    def __init__(self, current_shortcuts, parent=None):
        super().__init__(parent)
        self.current_shortcuts = current_shortcuts.copy()
        self.preferences_manager = PreferencesManager()
        self._setup_ui()
        self._load_shortcuts_to_table()
    
    def _setup_ui(self):
        """Setup the preferences dialog UI"""
        self.setWindowTitle("Preferencias - Atajos de Teclado")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Configurar Atajos de Teclado")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Haz clic en 'Cambiar' para asignar un nuevo atajo a cada herramienta.")
        instructions.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(instructions)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Herramienta", "Atajo Actual", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.restore_button = QPushButton("Restaurar Predeterminados")
        self.restore_button.clicked.connect(self._restore_defaults)
        button_layout.addWidget(self.restore_button)
        
        button_layout.addStretch()
        
        self.save_button = QPushButton("Guardar")
        self.save_button.clicked.connect(self._save_and_close)
        self.save_button.setStyleSheet("background-color: #1a73e8; color: white; padding: 5px 15px;")
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _load_shortcuts_to_table(self):
        """Load current shortcuts into the table"""
        self.table.setRowCount(len(self.current_shortcuts))
        
        row = 0
        for tool, (key_code, key_name) in self.current_shortcuts.items():
            # Tool name
            tool_display = self.preferences_manager.get_tool_name_display(tool)
            tool_item = QTableWidgetItem(tool_display)
            tool_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, tool_item)
            
            # Current shortcut
            shortcut_item = QTableWidgetItem(key_name)
            shortcut_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            shortcut_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            shortcut_item.setData(Qt.ItemDataRole.UserRole, tool)  # Store tool name
            self.table.setItem(row, 1, shortcut_item)
            
            # Change button
            change_button = QPushButton("Cambiar")
            change_button.clicked.connect(lambda checked, t=tool, r=row: self._change_shortcut(t, r))
            self.table.setCellWidget(row, 2, change_button)
            
            row += 1
    
    def _change_shortcut(self, tool, row):
        """Open dialog to change a shortcut"""
        dialog = KeyCaptureDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            key_code, key_name = dialog.get_captured_key()
            if key_code and key_name:
                # Check if this key is already used
                for other_tool, (other_key, _) in self.current_shortcuts.items():
                    if other_tool != tool and other_key == key_code:
                        tool_display = self.preferences_manager.get_tool_name_display(other_tool)
                        QMessageBox.warning(
                            self,
                            "Atajo Duplicado",
                            f"El atajo '{key_name}' ya está asignado a '{tool_display}'.\n"
                            f"Por favor elige otro atajo."
                        )
                        return
                
                # Update the shortcut
                self.current_shortcuts[tool] = (key_code, key_name)
                self.table.item(row, 1).setText(key_name)
    
    def _restore_defaults(self):
        """Restore default shortcuts"""
        reply = QMessageBox.question(
            self,
            "Restaurar Predeterminados",
            "¿Estás seguro de que quieres restaurar los atajos predeterminados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.current_shortcuts = self.preferences_manager.default_shortcuts.copy()
            self._load_shortcuts_to_table()
    
    def _save_and_close(self):
        """Save shortcuts and close dialog"""
        # Validate
        is_valid, error_msg = self.preferences_manager.validate_shortcuts(self.current_shortcuts)
        if not is_valid:
            QMessageBox.warning(self, "Error de Validación", error_msg)
            return
        
        # Save to CSV
        if self.preferences_manager.save_shortcuts(self.current_shortcuts):
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudieron guardar las preferencias.")
    
    def get_shortcuts(self):
        """Return the updated shortcuts dictionary"""
        return self.current_shortcuts
