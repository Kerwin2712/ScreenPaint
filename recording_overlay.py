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
        
        # Calculate Frame Rect (Excluding controls at bottom)
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        
        painter.drawRect(0, 0, self.width(), frame_h)
        
        # Resize handles visual
        painter.setBrush(self.border_color)
        handle_size = 10
        
        # Bottom-Right
        painter.drawRect(self.width()-handle_size, frame_h-handle_size, handle_size, handle_size)
        
        # Top-Left
        painter.drawRect(0, 0, handle_size, handle_size)

        # Top-Right
        painter.drawRect(self.width()-handle_size, 0, handle_size, handle_size)

        # Bottom-Left
        painter.drawRect(0, frame_h-handle_size, handle_size, handle_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            
            ctrl_h = self.control_bar.height()
            frame_h = self.height() - ctrl_h
            w = self.width()
            
            # Hit detection tolerance
            t = 20 

            # Bottom-Right
            if (w - pos.x() < t) and (abs(frame_h - pos.y()) < t):
                self.is_resizing = True
                self.resize_edge = 'bottom_right'
                self.drag_start_pos = pos
                
            # Top-Left
            elif (pos.x() < t) and (pos.y() < t):
                self.is_resizing = True
                self.resize_edge = 'top_left'
                self.drag_start_global = event.globalPosition().toPoint()
                self.drag_start_geo = self.geometry()
            
            # Top-Right
            elif (w - pos.x() < t) and (pos.y() < t):
                self.is_resizing = True
                self.resize_edge = 'top_right'
                self.drag_start_global = event.globalPosition().toPoint()
                self.drag_start_geo = self.geometry()

            # Bottom-Left
            elif (pos.x() < t) and (abs(frame_h - pos.y()) < t):
                self.is_resizing = True
                self.resize_edge = 'bottom_left'
                self.drag_start_global = event.globalPosition().toPoint()
                self.drag_start_geo = self.geometry()
                
            # Top drag area (simulated title bar) - Top of Frame
            elif pos.y() < 30 and pos.x() < w - 30: 
                self.is_dragging = True
                self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
            # Drag anywhere empty in the frame
            elif pos.y() < frame_h and not self.control_bar.geometry().contains(pos):
                  self.is_dragging = True
                  self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        w = self.width()
        t = 20
        
        # Cursor update
        # TL-BR should be BDiag (\)
        if ((w - pos.x() < t) and (abs(frame_h - pos.y()) < t)) or ((pos.x() < t) and (pos.y() < t)):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        # TR-BL should be FDiag (/)
        elif ((w - pos.x() < t) and (pos.y() < t)) or ((pos.x() < t) and (abs(frame_h - pos.y()) < t)):
             self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
        if self.is_resizing:
            global_pos = event.globalPosition().toPoint()
            
            # TL, TR, BL use global geometry calculation
            # BR uses local resize logic (simplest for BR)
            
            orig_geo = getattr(self, 'drag_start_geo', self.geometry())
            orig_tl = orig_geo.topLeft()
            orig_br = orig_geo.bottomRight()
            
            if self.resize_edge == 'bottom_right':
                tl = self.geometry().topLeft()
                new_w = max(100, global_pos.x() - tl.x())
                new_frame_h = max(50, global_pos.y() - tl.y())
                self.resize(new_w, new_frame_h + ctrl_h)
            
            elif self.resize_edge == 'top_left':
                new_x = min(global_pos.x(), orig_br.x() - 100)
                new_y = min(global_pos.y(), orig_br.y() - 100)
                new_w = orig_br.x() - new_x + 1
                new_h = orig_br.y() - new_y + 1
                self.setGeometry(new_x, new_y, new_w, new_h)

            elif self.resize_edge == 'top_right':
                # Anchor: Bottom-Left
                orig_bl_x = orig_geo.x()
                orig_bl_y = orig_geo.y() + orig_geo.height()
                
                # New Top (Y)
                new_y = min(global_pos.y(), orig_bl_y - 100)
                
                # New Width (based on Mouse X - Left X)
                # Global Mouse X is the new Right edge
                # Left edge stays at orig_bl_x
                new_w = max(100, global_pos.x() - orig_bl_x)
                
                # Height
                new_h = orig_bl_y - new_y
                
                self.setGeometry(orig_bl_x, new_y, new_w, new_h)

            elif self.resize_edge == 'bottom_left':
                # Anchor: Top-Right
                orig_tr_x = orig_geo.x() + orig_geo.width()
                orig_tr_y = orig_geo.y()
                
                # New Left (X)
                new_x = min(global_pos.x(), orig_tr_x - 100)
                
                # New Frame Height (Mouse Y - Top Y)
                new_frame_h = max(50, global_pos.y() - orig_tr_y)
                
                # Window Height = Frame H + Ctrl H
                new_h = new_frame_h + ctrl_h
                
                # Width
                new_w = orig_tr_x - new_x
                
                self.setGeometry(new_x, orig_tr_y, new_w, new_h)
            
        elif self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.is_resizing = False
        self.resize_edge = None

    def get_capture_rect(self):
        # Calculate current capture rect (Inner area)
        geo = self.geometry()
        b = self.border_width
        
        # Capture area is Window Height - Control Bar Height
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        
        # Global position
        global_pos = self.mapToGlobal(QPoint(0, 0))
        x, y = global_pos.x(), global_pos.y()
        w = self.width()
        
        # Inner rect (excluding border)
        return QRect(x + b, y + b, w - 2*b, frame_h - 2*b)

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
        
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        
        # Capture rect relative to screen
        global_pos = self.mapToGlobal(QPoint(0, 0))
        x, y = global_pos.x(), global_pos.y()
        w = self.width()
        
        rect = QRect(x + b, y + b, w - 2*b, frame_h - 2*b)
        
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

