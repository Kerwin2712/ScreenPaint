"""
Preferences Dialog.
Ventana de preferencias con pestañas para:
- Atajos de teclado
- Orden de botones
- Visibilidad de herramientas
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
                                QHeaderView, QTabWidget, QWidget, QListWidget, QCheckBox,
                                QGroupBox)
from PyQt6.QtCore import Qt
from ui.key_capture_dialog import KeyCaptureDialog          # import actualizado
from config.preferences_manager import PreferencesManager   # import actualizado

class PreferencesDialog(QDialog):
    def __init__(self, current_shortcuts, parent=None):
        super().__init__(parent)
        self.current_shortcuts = current_shortcuts.copy()
        self.preferences_manager = PreferencesManager()
        
        self.button_order = self.preferences_manager.load_button_order()
        self.tool_visibility = self.preferences_manager.load_tool_visibility()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura el diálogo con pestañas"""
        self.setWindowTitle("Preferencias")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        self.tabs.addTab(self._create_shortcuts_tab(), "Atajos de Teclado")
        self.tabs.addTab(self._create_button_order_tab(), "Orden de Botones")
        self.tabs.addTab(self._create_visibility_tab(), "Herramientas Visibles")
        
        layout.addWidget(self.tabs)
        
        button_layout = QHBoxLayout()
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
    
    # ===== PESTAÑA 1: ATAJOS =====
    
    def _create_shortcuts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel("Haz clic en 'Cambiar' para asignar un nuevo atajo a cada herramienta.")
        instructions.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(instructions)
        
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(3)
        self.shortcuts_table.setHorizontalHeaderLabels(["Herramienta", "Atajo Actual", ""])
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.shortcuts_table.verticalHeader().setVisible(False)
        self.shortcuts_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        layout.addWidget(self.shortcuts_table)
        
        self._load_shortcuts_to_table()
        
        restore_button = QPushButton("Restaurar Predeterminados")
        restore_button.clicked.connect(self._restore_default_shortcuts)
        layout.addWidget(restore_button)
        
        tab.setLayout(layout)
        return tab
    
    def _load_shortcuts_to_table(self):
        self.shortcuts_table.setRowCount(len(self.current_shortcuts))
        
        row = 0
        for tool, (key_code, key_name) in self.current_shortcuts.items():
            tool_display = self.preferences_manager.get_tool_name_display(tool)
            tool_item = QTableWidgetItem(tool_display)
            tool_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.shortcuts_table.setItem(row, 0, tool_item)
            
            shortcut_item = QTableWidgetItem(key_name)
            shortcut_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            shortcut_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            shortcut_item.setData(Qt.ItemDataRole.UserRole, tool)
            self.shortcuts_table.setItem(row, 1, shortcut_item)
            
            change_button = QPushButton("Cambiar")
            change_button.clicked.connect(lambda checked, t=tool, r=row: self._change_shortcut(t, r))
            self.shortcuts_table.setCellWidget(row, 2, change_button)
            
            row += 1
    
    def _change_shortcut(self, tool, row):
        dialog = KeyCaptureDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            key_code, key_name = dialog.get_captured_key()
            if key_code and key_name:
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
                
                self.current_shortcuts[tool] = (key_code, key_name)
                self.shortcuts_table.item(row, 1).setText(key_name)
    
    def _restore_default_shortcuts(self):
        reply = QMessageBox.question(
            self,
            "Restaurar Predeterminados",
            "¿Estás seguro de que quieres restaurar los atajos predeterminados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.current_shortcuts = self.preferences_manager.default_shortcuts.copy()
            self._load_shortcuts_to_table()
    
    # ===== PESTAÑA 2: ORDEN DE BOTONES =====
    
    def _create_button_order_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel("Usa los botones para reordenar las herramientas del menú.")
        instructions.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(instructions)
        
        self.order_list = QListWidget()
        for button_id in self.button_order:
            button_name = self.preferences_manager.get_button_name_display(button_id)
            self.order_list.addItem(f"{button_name}")
            self.order_list.item(self.order_list.count() - 1).setData(Qt.ItemDataRole.UserRole, button_id)
        layout.addWidget(self.order_list)
        
        button_layout = QHBoxLayout()
        
        move_up_btn = QPushButton("▲ Subir")
        move_up_btn.clicked.connect(self._move_button_up)
        button_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("▼ Bajar")
        move_down_btn.clicked.connect(self._move_button_down)
        button_layout.addWidget(move_down_btn)
        
        button_layout.addStretch()
        
        restore_order_btn = QPushButton("Restaurar Predeterminados")
        restore_order_btn.clicked.connect(self._restore_default_order)
        button_layout.addWidget(restore_order_btn)
        
        layout.addLayout(button_layout)
        tab.setLayout(layout)
        return tab
    
    def _move_button_up(self):
        current_row = self.order_list.currentRow()
        if current_row > 0:
            item = self.order_list.takeItem(current_row)
            self.order_list.insertItem(current_row - 1, item)
            self.order_list.setCurrentRow(current_row - 1)
            self.button_order.insert(current_row - 1, self.button_order.pop(current_row))
    
    def _move_button_down(self):
        current_row = self.order_list.currentRow()
        if current_row < self.order_list.count() - 1 and current_row >= 0:
            item = self.order_list.takeItem(current_row)
            self.order_list.insertItem(current_row + 1, item)
            self.order_list.setCurrentRow(current_row + 1)
            self.button_order.insert(current_row + 1, self.button_order.pop(current_row))
    
    def _restore_default_order(self):
        reply = QMessageBox.question(
            self,
            "Restaurar Predeterminados",
            "¿Estás seguro de que quieres restaurar el orden predeterminado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.button_order = self.preferences_manager.default_button_order.copy()
            self.order_list.clear()
            for button_id in self.button_order:
                button_name = self.preferences_manager.get_button_name_display(button_id)
                self.order_list.addItem(f"{button_name}")
                self.order_list.item(self.order_list.count() - 1).setData(Qt.ItemDataRole.UserRole, button_id)
    
    # ===== PESTAÑA 3: VISIBILIDAD =====
    
    def _create_visibility_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel("Selecciona las herramientas que deseas mostrar en el menú.")
        instructions.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(instructions)
        
        self.visibility_checkboxes = {}
        for button_id in self.preferences_manager.default_button_order:
            button_name = self.preferences_manager.get_button_name_display(button_id)
            checkbox = QCheckBox(button_name)
            checkbox.setChecked(self.tool_visibility.get(button_id, True))
            self.visibility_checkboxes[button_id] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Seleccionar Todo")
        select_all_btn.clicked.connect(self._select_all_visibility)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deseleccionar Todo")
        deselect_all_btn.clicked.connect(self._deselect_all_visibility)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        restore_vis_btn = QPushButton("Restaurar Predeterminados")
        restore_vis_btn.clicked.connect(self._restore_default_visibility)
        button_layout.addWidget(restore_vis_btn)
        
        layout.addLayout(button_layout)
        tab.setLayout(layout)
        return tab
    
    def _select_all_visibility(self):
        for checkbox in self.visibility_checkboxes.values():
            checkbox.setChecked(True)
    
    def _deselect_all_visibility(self):
        for checkbox in self.visibility_checkboxes.values():
            checkbox.setChecked(False)
    
    def _restore_default_visibility(self):
        reply = QMessageBox.question(
            self,
            "Restaurar Predeterminados",
            "¿Estás seguro de que quieres restaurar la visibilidad predeterminada?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.tool_visibility = self.preferences_manager.default_visibility.copy()
            for button_id, checkbox in self.visibility_checkboxes.items():
                checkbox.setChecked(self.tool_visibility.get(button_id, True))
    
    # ===== GUARDAR =====
    
    def _save_and_close(self):
        """Guarda todas las preferencias y cierra el diálogo"""
        is_valid, error_msg = self.preferences_manager.validate_shortcuts(self.current_shortcuts)
        if not is_valid:
            QMessageBox.warning(self, "Error de Validación", error_msg)
            return
        
        self.tool_visibility = {button_id: cb.isChecked() 
                                for button_id, cb in self.visibility_checkboxes.items()}
        
        success = True
        success = success and self.preferences_manager.save_shortcuts(self.current_shortcuts)
        success = success and self.preferences_manager.save_button_order(self.button_order)
        success = success and self.preferences_manager.save_tool_visibility(self.tool_visibility)
        
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudieron guardar las preferencias.")
    
    # ===== GETTERS =====
    
    def get_shortcuts(self):
        return self.current_shortcuts
    
    def get_button_order(self):
        return self.button_order
    
    def get_tool_visibility(self):
        return self.tool_visibility
