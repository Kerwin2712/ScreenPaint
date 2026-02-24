from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QFrame, QApplication, QProgressDialog
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor
from tools.capture_screen import ScreenRecorder, take_screenshot  # import actualizado
import os
import datetime
import time

class ResizableRubberBand(QWidget):
    """
    Ventana transparente redimensionable con borde para captura/grabación.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resize(400, 300)
        self.setMinimumSize(100, 100)
        
        self.is_dragging = False
        self.is_resizing = False
        self.resize_edge = None
        self.drag_start_pos = QPoint()
        self.audio_enabled = True
        self.is_paused = False
        
        self.border_color = QColor(255, 0, 0)
        self.border_width = 4
        
        self._init_ui()
        
        self.recorder = None
        self.progress_dialog = None
        
    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addStretch()
        
        self.control_bar = QFrame()
        self.control_bar.setStyleSheet("background-color: rgba(0, 0, 0, 150); border-radius: 5px;")
        self.control_bar.setFixedHeight(40)
        
        btn_layout = QHBoxLayout(self.control_bar)
        btn_layout.setContentsMargins(5, 0, 5, 0)
        
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
        
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        
        painter.drawRect(0, 0, self.width(), frame_h)
        
        painter.setBrush(self.border_color)
        handle_size = 10
        
        painter.drawRect(self.width()-handle_size, frame_h-handle_size, handle_size, handle_size)
        painter.drawRect(0, 0, handle_size, handle_size)
        painter.drawRect(self.width()-handle_size, 0, handle_size, handle_size)
        painter.drawRect(0, frame_h-handle_size, handle_size, handle_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            
            ctrl_h = self.control_bar.height()
            frame_h = self.height() - ctrl_h
            w = self.width()
            t = 20

            if (w - pos.x() < t) and (abs(frame_h - pos.y()) < t):
                self.is_resizing = True
                self.resize_edge = 'bottom_right'
                self.drag_start_pos = pos
                
            elif (pos.x() < t) and (pos.y() < t):
                self.is_resizing = True
                self.resize_edge = 'top_left'
                self.drag_start_global = event.globalPosition().toPoint()
                self.drag_start_geo = self.geometry()
            
            elif (w - pos.x() < t) and (pos.y() < t):
                self.is_resizing = True
                self.resize_edge = 'top_right'
                self.drag_start_global = event.globalPosition().toPoint()
                self.drag_start_geo = self.geometry()

            elif (pos.x() < t) and (abs(frame_h - pos.y()) < t):
                self.is_resizing = True
                self.resize_edge = 'bottom_left'
                self.drag_start_global = event.globalPosition().toPoint()
                self.drag_start_geo = self.geometry()
                
            elif pos.y() < 30 and pos.x() < w - 30: 
                self.is_dragging = True
                self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
            elif pos.y() < frame_h and not self.control_bar.geometry().contains(pos):
                self.is_dragging = True
                self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        w = self.width()
        t = 20
        
        if ((w - pos.x() < t) and (abs(frame_h - pos.y()) < t)) or ((pos.x() < t) and (pos.y() < t)):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif ((w - pos.x() < t) and (pos.y() < t)) or ((pos.x() < t) and (abs(frame_h - pos.y()) < t)):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
        if self.is_resizing:
            global_pos = event.globalPosition().toPoint()
            
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
                orig_bl_x = orig_geo.x()
                orig_bl_y = orig_geo.y() + orig_geo.height()
                new_y = min(global_pos.y(), orig_bl_y - 100)
                new_w = max(100, global_pos.x() - orig_bl_x)
                new_h = orig_bl_y - new_y
                self.setGeometry(orig_bl_x, new_y, new_w, new_h)

            elif self.resize_edge == 'bottom_left':
                orig_tr_x = orig_geo.x() + orig_geo.width()
                orig_tr_y = orig_geo.y()
                new_x = min(global_pos.x(), orig_tr_x - 100)
                new_frame_h = max(50, global_pos.y() - orig_tr_y)
                new_h = new_frame_h + ctrl_h
                new_w = orig_tr_x - new_x
                self.setGeometry(new_x, orig_tr_y, new_w, new_h)
            
        elif self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.is_resizing = False
        self.resize_edge = None

    def get_capture_rect(self):
        geo = self.geometry()
        b = self.border_width
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        global_pos = self.mapToGlobal(QPoint(0, 0))
        x, y = global_pos.x(), global_pos.y()
        w = self.width()
        return QRect(x + b, y + b, w - 2*b, frame_h - 2*b)

    def start_recording(self):
        if not self.recorder:
            fname, _ = QFileDialog.getSaveFileName(self, "Guardar Video", "", "Video Files (*.mp4)")
            if not fname: return
            if not fname.endswith('.mp4'): fname += '.mp4'
            
            self.recorder = ScreenRecorder(geometry_source=self.get_capture_rect, output_filename=fname, audio_enabled=self.audio_enabled)
            self.recorder.recording_stopped.connect(self.on_recording_finished)
            self.recorder.processing_started.connect(self.on_processing_started)
            self.recorder.start()
            
            self.btn_rec.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_snap.setEnabled(True)
            self.border_color = QColor(0, 255, 0)
            self.update()

    def stop_recording(self):
        if self.recorder:
            self.recorder.stop()
            
    def toggle_pause(self):
        if self.recorder:
            self.recorder.pause()
            self.is_paused = not self.is_paused
            
            if self.is_paused:
                self.border_color = QColor(255, 255, 0)
            else:
                self.border_color = QColor(0, 255, 0)
            self.update()
            
    def on_processing_started(self):
        self.progress_dialog = QProgressDialog("Procesando video... Por favor espere.", None, 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()
        QApplication.processEvents()
            
    def on_recording_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
        self.recorder = None
        self.btn_rec.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.border_color = QColor(255, 0, 0)
        self.update()

    def take_snapshot(self):
        geo = self.geometry()
        b = self.border_width
        ctrl_h = self.control_bar.height()
        frame_h = self.height() - ctrl_h
        global_pos = self.mapToGlobal(QPoint(0, 0))
        x, y = global_pos.x(), global_pos.y()
        w = self.width()
        
        rect = QRect(x + b, y + b, w - 2*b, frame_h - 2*b)
        
        prev_opacity = self.windowOpacity()
        self.setWindowOpacity(0)
        QApplication.processEvents()
        
        time.sleep(0.1)
        
        if self.recorder:
            video_path = self.recorder.output_filename
            video_dir = os.path.dirname(video_path)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = os.path.join(video_dir, f"snapshot_{timestamp}.png")
            take_screenshot(rect=rect, filename=fname)
        else:
            fname, _ = QFileDialog.getSaveFileName(self, "Guardar Imagen", "", "PNG Files (*.png)")
            if fname:
                take_screenshot(rect=rect, filename=fname)
            
        self.setWindowOpacity(prev_opacity)
