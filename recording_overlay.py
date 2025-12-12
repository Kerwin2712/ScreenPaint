from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QFrame
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor
from capture_screen import ScreenRecorder, take_screenshot

class ResizableRubberBand(QWidget):
    """
    A transparent resizeable window with a border.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Geometry
        self.resize(400, 300)
        self.setMinimumSize(100, 100)
        
        # State
        self.is_dragging = False
        self.is_resizing = False
        self.resize_edge = None
        self.drag_start_pos = QPoint()
        
        # Border style
        self.border_color = QColor(255, 0, 0)
        self.border_width = 4
        
        # Control UI
        self._init_ui()
        
        # Recorder
        self.recorder = None
        self.is_paused = False

    def _init_ui(self):
        # Layout for controls (Attached to bottom or top?)
        # Let's put a control bar at the bottom inside the frame area, implies it covers content? 
        # Better: Put it BELOW the frame if possible, or overlay at bottom.
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addStretch()
        
        self.control_bar = QFrame()
        self.control_bar.setStyleSheet("background-color: rgba(0, 0, 0, 150); border-radius: 5px;")
        self.control_bar.setFixedHeight(40)
        
        btn_layout = QHBoxLayout(self.control_bar)
        btn_layout.setContentsMargins(5, 0, 5, 0)
        
        # Buttons
        self.btn_rec = QPushButton("🔴")
        self.btn_rec.setToolTip("Grabar")
        self.btn_rec.clicked.connect(self.start_recording)
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setToolTip("Pausar")
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False)
        
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setToolTip("Detener y Guardar")
        self.btn_stop.clicked.connect(self.stop_recording)
        self.btn_stop.setEnabled(False)
        
        self.btn_snap = QPushButton("📷")
        self.btn_snap.setToolTip("Capturar Imagen")
        self.btn_snap.clicked.connect(self.take_snapshot)
        
        self.btn_close = QPushButton("❌")
        self.btn_close.clicked.connect(self.close)
        
        style = """
            QPushButton {
                background-color: transparent; 
                border: none; 
                font-size: 16px; 
                color: white;
            }
            QPushButton:hover { background-color: rgba(255,255,255,50); border-radius: 3px;}
        """
        self.control_bar.setStyleSheet(self.control_bar.styleSheet() + style)
        
        btn_layout.addWidget(self.btn_rec)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_snap)
        btn_layout.addWidget(self.btn_close)
        
        self.main_layout.addWidget(self.control_bar)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Resize handles visual
        painter.setBrush(self.border_color)
        handle_size = 10
        # Bottom-Right
        painter.drawRect(self.width()-handle_size, self.height()-handle_size, handle_size, handle_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            # Check resize handle (Bottom Right)
            if (self.width() - pos.x() < 20) and (self.height() - pos.y() < 20):
                self.is_resizing = True
                self.resize_edge = 'bottom_right'
                self.drag_start_pos = pos
            elif pos.y() < 30 and pos.x() < self.width() - 30: # Top drag area (simulated title bar) or just drag anywhere not control?
                # Let's verify if clicking on controls
                # The generic mouse press arrives here if not consumed by child widget?
                # If clicking on control bar, it might be consumed.
                # Let's allow dragging from top header area
                self.is_dragging = True
                self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
            # Simple "drag anywhere empty"
            elif not self.control_bar.geometry().contains(pos):
                self.is_dragging = True
                self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        # Cursor update
        if (self.width() - pos.x() < 20) and (self.height() - pos.y() < 20):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
        if self.is_resizing:
            delta = pos - self.drag_start_pos # This logic is tricky for resize
            # simpler: set geometry based on global mouse pos
            global_pos = event.globalPosition().toPoint()
            current_geo = self.geometry()
            new_w = max(100, global_pos.x() - current_geo.x())
            new_h = max(100, global_pos.y() - current_geo.y())
            self.resize(new_w, new_h)
            
        elif self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.is_resizing = False

    def get_capture_rect(self):
        # Calculate current capture rect (Inner area)
        geo = self.geometry()
        b = self.border_width
        # Determine capture area. We ignore the control bar height for the capture?
        # User wants to capture "the rectangle".
        # Let's capture the area INSIDE the red border. 
        # Control bar is overlaying, but if we resize window, control bar stays at bottom.
        # Let's capture the full inner rect including control bar area if it overlaps content?
        # No, control bar should probably be excluded if possible, or user accepts it.
        # But wait, self.control_bar is a child widget. 
        # The window is transparent.
        # If we grabWindow of the *screen* coordinates, we get whatever is there.
        # We should calculate the rect relative to screen.
        
        # Global position
        global_pos = self.mapToGlobal(QPoint(0, 0))
        x, y = global_pos.x(), global_pos.y()
        w, h = self.width(), self.height()
        
        # Inner rect
        return QRect(x + b, y + b, w - 2*b, h - 2*b)

    def start_recording(self):
        if not self.recorder:
            fname, _ = QFileDialog.getSaveFileName(self, "Guardar Video", "", "AVI Files (*.avi)")
            if not fname: return
            if not fname.endswith('.avi'): fname += '.avi'
            
            # Use Dynamic Geometry Source
            self.recorder = ScreenRecorder(geometry_source=self.get_capture_rect, output_filename=fname)
            self.recorder.recording_stopped.connect(self.on_recording_finished)
            self.recorder.start()
            
            self.btn_rec.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_snap.setEnabled(True)
            self.border_color = QColor(0, 255, 0) # Green when recording
            self.update()

    def stop_recording(self):
        if self.recorder:
            self.recorder.stop()
            
    def toggle_pause(self):
        if self.recorder:
            self.recorder.pause()
            self.is_paused = not self.is_paused
            
            if self.is_paused:
                self.border_color = QColor(255, 255, 0) # Yellow
            else:
                self.border_color = QColor(0, 255, 0) # Green
            self.update()
            
    def on_recording_finished(self):
        self.recorder = None
        self.btn_rec.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.border_color = QColor(255, 0, 0)
        self.update()

    def take_snapshot(self):
        # Similar rect logic
        geo = self.geometry()
        b = self.border_width
        rect = QRect(geo.x() + b, geo.y() + b, geo.width() - 2*b, geo.height() - 2*b - self.control_bar.height())
        
        # Hide self briefly to avoid capturing border?
        prev_opacity = self.windowOpacity()
        self.setWindowOpacity(0) # Hide
        QApplication.processEvents() # Update UI
        
        import time
        time.sleep(0.1) # Wait for composition
        
        fname, _ = QFileDialog.getSaveFileName(self, "Guardar Imagen", "", "PNG Files (*.png)")
        if fname:
            take_screenshot(rect=rect, filename=fname)
            
        self.setWindowOpacity(prev_opacity)

