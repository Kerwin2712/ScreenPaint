"""
Preferences Manager for ScreenPaint
Handles loading, saving, and validation of user preferences
Stores keyboard shortcuts in CSV format
"""

import csv
import os
from PyQt6.QtCore import Qt

class PreferencesManager:
    def __init__(self, preferences_file='preferences.csv'):
        self.preferences_file = preferences_file
        self.default_shortcuts = self._get_default_shortcuts()
    
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
