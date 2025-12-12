import cv2
import numpy as np
import datetime
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QRect
from PyQt6.QtGui import QImage

def take_screenshot(rect=None, filename=None):
    """
    Takes a screenshot of the specified rect (QRect) or full screen if rect is None.
    Saves to filename if provided, otherwise generates a timestamped filename.
    Returns the filename saved.
    """
    screen = QApplication.primaryScreen()
    if not screen:
        return None
        
    if rect:
        # grabWindow takes: windowId, x, y, w, h
        # We pass 0 as windowId to grab desktop/screen
        pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
    else:
        pixmap = screen.grabWindow(0)
        
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        
    pixmap.save(filename)
    return filename

class ScreenRecorder(QThread):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, rect=None, geometry_source=None, output_filename=None):
        super().__init__()
        self.rect = rect # Initial QRect (Static)
        self.geometry_source = geometry_source # Callable returning QRect (Dynamic)
        self.output_filename = output_filename
        self.is_recording = False
        self.is_paused = False
        self._fps = 20.0
        
    def run(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.error_occurred.emit("No primary screen found")
            return

        # Determine Initial Geometry and Fixed Output Size
        if self.rect:
            current_geom = self.rect
        elif self.geometry_source:
            current_geom = self.geometry_source()
        else:
            current_geom = screen.geometry() # Fullscreen
            
        x, y, w, h = current_geom.x(), current_geom.y(), current_geom.width(), current_geom.height()
        
        # Output Size is FIXED based on start settings
        out_w, out_h = w, h
        
        if not self.output_filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_filename = f"recording_{timestamp}.avi"

        # Codec
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(self.output_filename, fourcc, self._fps, (out_w, out_h))

        self.is_recording = True
        self.recording_started.emit()

        try:
            while self.is_recording:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                start_time = time.time()
                
                # Get Current Geometry if dynamic
                if self.geometry_source:
                    current_geom = self.geometry_source()
                    x, y, w, h = current_geom.x(), current_geom.y(), current_geom.width(), current_geom.height()
                
                # Grab Frame
                # grabbing from window ID 0 (Desktop)
                pixmap = screen.grabWindow(0, x, y, w, h)
                image = pixmap.toImage()
                
                # Convert QImage to Numpy Array
                image = image.convertToFormat(QImage.Format.Format_RGB32)
                
                width = image.width()
                height = image.height()
                
                ptr = image.bits()
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                
                frame = arr[:, :, :3] # BGR (or RGB depending on system)
                # Convert to BGR if needed (Usually needed for RGB32)
                # Ideally check channel order but standard is usually needing conversion
                # Let's assume standard BGR for now as per previous logic.
                
                # Resize if dimensions changed (Zoom Effect)
                if width != out_w or height != out_h:
                    frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
                    
                out.write(frame)
                
                # FPS Control
                
                # FPS Control
                elapsed = time.time() - start_time
                wait_time = max(0, (1.0/self._fps) - elapsed)
                time.sleep(wait_time)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            out.release()
            self.recording_stopped.emit()

    def stop(self):
        self.is_recording = False
        self.wait()

    def pause(self):
        self.is_paused = not self.is_paused

