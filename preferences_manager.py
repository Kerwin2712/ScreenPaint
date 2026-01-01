"""
Preferences Manager for ScreenPaint
Handles loading, saving, and validation of user preferences
Stores keyboard shortcuts, button order, and tool visibility in CSV format
"""

import csv
import os
from PyQt6.QtCore import Qt

class PreferencesManager:
    def __init__(self, preferences_file='preferences.csv', 
                 button_order_file='button_order.csv',
                 visibility_file='tool_visibility.csv'):
        self.preferences_file = preferences_file
        self.button_order_file = button_order_file
        self.visibility_file = visibility_file
        self.default_shortcuts = self._get_default_shortcuts()
        self.default_button_order = self._get_default_button_order()
        self.default_visibility = self._get_default_visibility()
    
    # ===== KEYBOARD SHORTCUTS =====
    
    def _get_default_shortcuts(self):
        """Return default keyboard shortcuts for tools"""
        return {
            'pen': (Qt.Key.Key_Alt, 'Alt'),
            'hand': (Qt.Key.Key_Shift, 'Shift'),
            'point': (Qt.Key.Key_P, 'P'),
            'segment': (Qt.Key.Key_L, 'L'),
            'circle_center_point': (Qt.Key.Key_C, 'C'),
            'rectangle': (Qt.Key.Key_R, 'R'),
            'eraser': (Qt.Key.Key_E, 'E'),
            'paint': (Qt.Key.Key_B, 'B'),
        }
    
    def load_shortcuts(self):
        """Load shortcuts from CSV file, create with defaults if doesn't exist"""
        if not os.path.exists(self.preferences_file):
            self.save_shortcuts(self.default_shortcuts)
            return self.default_shortcuts.copy()
        
        shortcuts = {}
        try:
            with open(self.preferences_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tool = row['tool']
                    key_code = int(row['key_code'])
                    key_name = row['key_name']
                    shortcuts[tool] = (key_code, key_name)
        except Exception as e:
            print(f"Error loading preferences: {e}")
            return self.default_shortcuts.copy()
        
        return shortcuts
    
    def save_shortcuts(self, shortcuts):
        """Save shortcuts to CSV file"""
        try:
            with open(self.preferences_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['tool', 'key_code', 'key_name'])
                for tool, (key_code, key_name) in shortcuts.items():
                    writer.writerow([tool, key_code, key_name])
            return True
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False
    
    def validate_shortcuts(self, shortcuts):
        """
        Validate that there are no duplicate shortcuts
        Returns (is_valid, error_message)
        """
        used_keys = {}
        for tool, (key_code, key_name) in shortcuts.items():
            if key_code in used_keys:
                return False, f"El atajo '{key_name}' ya está asignado a '{used_keys[key_code]}'"
            used_keys[key_code] = tool
        return True, ""
    
    # ===== BUTTON ORDER =====
    
    def _get_default_button_order(self):
        """Return default button order"""
        return [
            'grip', 'pen', 'line', 'shapes', 'camera',
            'hand', 'paint', 'text', 'undo', 'redo', 'eraser',
            'clear', 'preferences', 'close'
        ]
    
    def load_button_order(self):
        """Load button order from CSV"""
        if not os.path.exists(self.button_order_file):
            self.save_button_order(self.default_button_order)
            return self.default_button_order.copy()
        
        button_order = []
        try:
            with open(self.button_order_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Sort by position and extract button_id
                rows = sorted(reader, key=lambda r: int(r['position']))
                button_order = [row['button_id'] for row in rows]
        except Exception as e:
            print(f"Error loading button order: {e}")
            return self.default_button_order.copy()
        
        return button_order if button_order else self.default_button_order.copy()
    
    def save_button_order(self, button_order):
        """Save button order to CSV"""
        try:
            with open(self.button_order_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['position', 'button_id'])
                for i, button_id in enumerate(button_order):
                    writer.writerow([i, button_id])
            return True
        except Exception as e:
            print(f"Error saving button order: {e}")
            return False
    
    # ===== TOOL VISIBILITY =====
    
    def _get_default_visibility(self):
        """Return default visibility for all tools"""
        return {
            'grip': True,
            'pen': True,
            'line': True,
            'shapes': True,
            'camera': True,
            'hand': True,
            'paint': True,
            'text': True,
            'undo': True,
            'redo': True,
            'eraser': True,
            'clear': True,
            'preferences': True,
            'close': True,
        }
    
    def load_tool_visibility(self):
        """Load tool visibility from CSV"""
        if not os.path.exists(self.visibility_file):
            self.save_tool_visibility(self.default_visibility)
            return self.default_visibility.copy()
        
        visibility = {}
        try:
            with open(self.visibility_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    button_id = row['button_id']
                    visible = row['visible'].lower() == 'true'
                    visibility[button_id] = visible
        except Exception as e:
            print(f"Error loading tool visibility: {e}")
            return self.default_visibility.copy()
        
        return visibility if visibility else self.default_visibility.copy()
    
    def save_tool_visibility(self, visibility):
        """Save tool visibility to CSV"""
        try:
            with open(self.visibility_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['button_id', 'visible'])
                for button_id, visible in visibility.items():
                    writer.writerow([button_id, str(visible).lower()])
            return True
        except Exception as e:
            print(f"Error saving tool visibility: {e}")
            return False
    
    # ===== UTILITY =====
    
    def get_tool_name_display(self, tool):
        """Get display name for tool"""
        tool_names = {
            'pen': 'Lápiz',
            'hand': 'Mano (Mover)',
            'point': 'Punto',
            'segment': 'Línea',
            'circle_center_point': 'Círculo',
            'rectangle': 'Rectángulo',
            'eraser': 'Borrador',
            'paint': 'Balde de Pintura',
        }
        return tool_names.get(tool, tool)
    
    def get_button_name_display(self, button_id):
        """Get display name for button"""
        button_names = {
            'grip': 'Mover/Minimizar Menú (✥)',
            'pen': 'Lápiz',
            'line': 'Líneas',
            'shapes': 'Figuras',
            'camera': 'Cámara',
            'hand': 'Mano (Mover Objetos)',
            'paint': 'Balde de Pintura',
            'text': 'Texto',
            'undo': 'Deshacer',
            'redo': 'Rehacer',
            'eraser': 'Borrador',
            'clear': 'Limpiar Todo',
            'preferences': 'Preferencias',
            'close': 'Cerrar',
        }
        return button_names.get(button_id, button_id)

