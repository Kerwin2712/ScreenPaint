from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QApplication, QProgressDialog
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from tools.capture_screen import ScreenRecorder, take_screenshot
import os
import datetime
import time


class ScreenRecordingOverlay(QWidget):
    """
    Overlay de pantalla completa con marco de color.
    Panel de control independiente y arrastrable.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # WA_TransparentForMouseEvents permite que el overlay de dibujo reciba clics
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Estado interno
        self.recorder        = None
        self.is_paused       = False
        self.audio_enabled   = True
        self._progress_dlg   = None

        # Colores de estado
        self.COLOR_IDLE  = QColor(220, 0,  0, 200)
        self.COLOR_REC   = QColor(0,  200, 0, 200)
        self.COLOR_PAUSE = QColor(220, 200, 0, 200)
        self.border_color = self.COLOR_IDLE
        self.BORDER_W     = 4

        # Cronómetro
        self.elapsed_secs = 0
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._on_tick)

        # Panel de control (ventana separada)
        self.panel = _ControlPanel()
        self.panel.btn_rec.clicked.connect(self.start_recording)
        self.panel.btn_pause.clicked.connect(self.toggle_pause)
        self.panel.btn_save.clicked.connect(self.save_and_stop)
        self.panel.btn_snap.clicked.connect(self.take_snapshot)
        self.panel.btn_close.clicked.connect(self.close_overlay)

        self._update_ui_state(recording=False, paused=False)

    # ------------------------------------------------------------------

    def show_overlay(self):
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        self.show()
        self.raise_()
        self._reposition_panel(screen_geo)
        self.panel.show()
        self.panel.raise_()

    def close_overlay(self):
        if self.recorder and self.recorder.isRunning():
            self.save_and_stop()
            return
        self.panel.hide()
        self.hide()

    def start_recording(self):
        if self.recorder and self.recorder.isRunning():
            return
        
        self.recorder = ScreenRecorder(audio_enabled=self.audio_enabled)
        self.recorder.recording_stopped.connect(self._on_stopped)
        self.recorder.processing_started.connect(self._on_processing_started)
        self.recorder.progress_updated.connect(self._on_progress)
        self.recorder.error_occurred.connect(lambda e: print(f"Recording Error: {e}"))
        
        self.recorder.start()
        self.elapsed_secs = 0
        self._ticker.start()
        self.border_color = self.COLOR_REC
        self.is_paused = False
        self._update_ui_state(recording=True, paused=False)
        self.update()

    def toggle_pause(self):
        if not self.recorder: return
        self.recorder.pause()
        self.is_paused = not self.is_paused
        self.border_color = self.COLOR_PAUSE if self.is_paused else self.COLOR_REC
        if self.is_paused: self._ticker.stop()
        else: self._ticker.start()
        self._update_ui_state(recording=True, paused=self.is_paused)
        self.update()

    def save_and_stop(self):
        if not self.recorder: return
        fname, _ = QFileDialog.getSaveFileName(self.panel, "Guardar Video", "", "Video MP4 (*.mp4)")
        if not fname: return
        if not fname.endswith('.mp4'): fname += '.mp4'
        
        self.recorder.output_filename = fname
        self.panel.hide()
        self._ticker.stop()
        self.border_color = self.COLOR_IDLE
        self.update()
        self.recorder.stop()

    def take_snapshot(self):
        self.hide()
        QApplication.processEvents()
        time.sleep(0.2)
        
        # Guardar captura
        if self.recorder and self.recorder.output_filename:
            d = os.path.dirname(self.recorder.output_filename) or "."
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            take_screenshot(filename=os.path.join(d, f"snapshot_{ts}.png"))
        else:
            fname, _ = QFileDialog.getSaveFileName(self.panel, "Guardar Imagen", "", "PNG (*.png)")
            if fname: take_screenshot(filename=fname)
        
        self.show()

    # ------------------------------------------------------------------

    def _on_tick(self):
        self.elapsed_secs += 1
        m, s = divmod(self.elapsed_secs, 60)
        self.panel.lbl_time.setText(f"{m:02d}:{s:02d}")
        self.update()

    def _on_processing_started(self):
        """Crear el diálogo de progreso garantizando que sea una instancia limpia."""
        self._progress_dlg = QProgressDialog("Guardando video...", None, 0, 100, None)
        self._progress_dlg.setWindowTitle("Guardado en curso")
        self._progress_dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress_dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self._progress_dlg.setCancelButton(None)
        self._progress_dlg.setMinimumDuration(0)
        self._progress_dlg.setMinimumWidth(350)
        self._progress_dlg.setValue(0)
        self._progress_dlg.show()
        # No usamos processEvents aquí para evitar reentrada de señales

    def _on_progress(self, pct: int):
        # Usar copia local de la referencia para evitar errores de NoneType
        p = self._progress_dlg
        if p is not None:
            try:
                p.setValue(pct)
                p.setLabelText(f"Guardando video... {pct}%")
            except:
                pass

    def _on_stopped(self):
        p = self._progress_dlg
        if p is not None:
            try:
                p.setValue(100)
                p.close()
            except:
                pass
            self._progress_dlg = None
        
        self.recorder = None
        self.is_paused = False
        self.elapsed_secs = 0
        self.panel.lbl_time.setText("")
        self._update_ui_state(recording=False, paused=False)
        self.panel.hide()
        self.hide()
        self.update()

    def _update_ui_state(self, recording, paused):
        self.panel.btn_rec.setEnabled(not recording)
        self.panel.btn_pause.setEnabled(recording)
        self.panel.btn_save.setEnabled(recording)
        self.panel.btn_pause.setText("RUN" if paused else "||")

    def _reposition_panel(self, screen_geo: QRect):
        self.panel.adjustSize()
        x = screen_geo.right() - self.panel.width() - 25
        y = screen_geo.bottom() - self.panel.height() - 45
        self.panel.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(self.border_color, self.BORDER_W))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        br = self.BORDER_W // 2
        painter.drawRect(br, br, self.width() - self.BORDER_W, self.height() - self.BORDER_W)
        
        if self.recorder:
            m, s = divmod(self.elapsed_secs, 60)
            status = "RECORD" if not self.is_paused else "PAUSED"
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            painter.setPen(self.border_color)
            painter.drawText(20, 25, f"{status} - {m:02d}:{s:02d}")


class _ControlPanel(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        btn_style = "background: #222; color: #EEE; border: 1px solid #555; border-radius: 4px; padding: 5px; min-width: 30px;"
        
        self.btn_rec   = QPushButton("REC");   self.btn_rec.setStyleSheet(btn_style)
        self.btn_pause = QPushButton("||");    self.btn_pause.setStyleSheet(btn_style)
        self.btn_save  = QPushButton("Save");  self.btn_save.setStyleSheet(btn_style)
        self.btn_snap  = QPushButton("Snap");  self.btn_snap.setStyleSheet(btn_style)
        self.btn_close = QPushButton("X");     self.btn_close.setStyleSheet(btn_style)
        self.lbl_time  = QLabel("00:00");      self.lbl_time.setStyleSheet("color: white; font-weight: bold;")
        
        for w in [self.btn_rec, self.btn_pause, self.btn_save, self.btn_snap, self.btn_close, self.lbl_time]:
            layout.addWidget(w)

        self.setStyleSheet("background: #333; border-radius: 8px;")
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
