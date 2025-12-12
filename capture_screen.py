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

    def __init__(self, rect=None, output_filename=None):
        super().__init__()
        self.rect = rect # QRect or None for fullscreen
        self.output_filename = output_filename
        self.is_recording = False
        self.is_paused = False
        self._fps = 20.0
        
    def run(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.error_occurred.emit("No primary screen found")
            return

        # Determine geometry
        if self.rect:
            x, y, w, h = self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height()
        else:
            geom = screen.geometry()
            x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()

        # Ensure even dimensions for video codec usually preferred, but not strictly required
        
        if not self.output_filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_filename = f"recording_{timestamp}.avi"

        # Codec
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(self.output_filename, fourcc, self._fps, (w, h))

        self.is_recording = True
        self.recording_started.emit()

        try:
            while self.is_recording:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                start_time = time.time()
                
                # Grab Frame
                # grabbing from window ID 0 (Desktop)
                pixmap = screen.grabWindow(0, x, y, w, h)
                image = pixmap.toImage()
                
                # Convert QImage to Numpy Array
                # QImage Format is usually ARGB32 or RGB32. 
                image = image.convertToFormat(QImage.Format.Format_RGB32)
                
                width = image.width()
                height = image.height()
                
                ptr = image.bits()
                # Reshape. Note: QImage.bits() returns a void pointer, we need to set size in bytes
                # For RGB32, it's 4 bytes per pixel.
                
                # Handling raw data robustly:
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                
                # Convert RGBA/BGRA to BGR for OpenCV
                # QImage is usually B G R A (little endian) -> BGR
                # But actually it depends. Format_RGB32 is 0xffRRGGBB.
                # Let's verify color channels.
                # OpenCV uses BGR.
                # Usually we just take the first 3 channels and flip if needed.
                
                frame = arr[:, :, :3] # Drop Alpha
                # If colors are swapped (blue face), we might need cvtColor
                # PyQt image is often BGRA on Windows. OpenCV wants BGR.
                # So taking [:3] gives BGR directly? Or RGB?
                # Usually RGB32 means B is at lowest byte address? 
                # Let's assume standard handling -> BGR is needed. 
                # It's safer to test, but I will assume it matches or might need cv2.COLOR_RGB2BGR or RGBA2BGR
                
                # Usually QImage ARGB32 -> B is 0, G is 1, R is 2. (Little Endian)
                # OpenCV wants BGR: B at 0, G at 1, R at 2.
                # So straight slicing might work.
                # If not, we use cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                
                # Actually, simpler:
                # frame = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR) 
                
                out.write(frame)
                
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

