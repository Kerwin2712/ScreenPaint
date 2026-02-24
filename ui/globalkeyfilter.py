from PyQt6.QtCore import QObject, QEvent, Qt
import time

class GlobalKeyFilter(QObject):
    def __init__(self, reset_callback):
        super().__init__()
        self.reset_callback = reset_callback
        self.last_alt_press_time = 0
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Alt:
                current_time = time.time()
                # Doble pulsación en menos de 400ms
                if current_time - self.last_alt_press_time < 0.4:
                    self.reset_callback()
                    self.last_alt_press_time = 0
                else:
                    self.last_alt_press_time = current_time
        return super().eventFilter(obj, event)
