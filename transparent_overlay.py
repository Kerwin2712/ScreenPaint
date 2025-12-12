import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QAction

class TransparentOverlay(QWidget):
    # Signal to notify main app to raise UI elements
    interacted = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # Window Configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Drawing State
        self.image = QPixmap()
        self.lastPoint = QPoint()
        self.drawing = False
        
        # Tools configuration
        self.brushSize = 3
        self.brushColor = Qt.GlobalColor.red
        self.eraserMode = False

        # Initialize Layout (Empty for now, logic controlled by Main)
        layout = QVBoxLayout()
        self.setLayout(layout)

    def resizeEvent(self, event):
        if self.image.isNull():
            self.image = QPixmap(self.size())
            # Use alpha=1 to capture mouse events
            self.image.fill(QColor(0, 0, 0, 1))
        else:
            # Handle resize: Create new pixmap, draw old one onto it?
            # For simplicity in this iteration, we just create a new larger canvas if needed
            # or keep the old one. A simple way is to scale or just keep the old one and draw on it if it fits.
            # Ideally, we create a new pixmap of the new size and draw the old one on it.
            new_image = QPixmap(self.size())
            new_image.fill(QColor(0, 0, 0, 1))
            painter = QPainter(new_image)
            painter.drawPixmap(0, 0, self.image)
            painter.end()
            self.image = new_image
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.image)

    def mousePressEvent(self, event):
        # Notify main to raise UI
        self.interacted.emit()
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.lastPoint = event.position().toPoint()

    def mouseMoveEvent(self, event):
        # Notify main to raise UI (frequency might be high, but ensures safety)
        # self.interacted.emit() 
        # Actually, let's emit only on press to avoid lag, or maybe on move if dragging into menu?
        # If I drag into menu, I want to be able to release.
        # But raising is cheap enough usually.
        # Let's keep it on Press for now. If user moves mouse over menu without pressing, overlay still has focus?
        # WA_ShowWithoutActivating should help.
        
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.drawing:
            painter = QPainter(self.image)
            
            if self.eraserMode:
                # Eraser Logic: We paint with the "background" color (alpha 1) instead of clearing to transparent
                # because clearing to transparent (alpha 0) would make it click-through again.
                # So the "Eraser" is effectively painting "invisible" ink that grabs events.
                pen = QPen(QColor(0, 0, 0, 1), 20, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source) # Overwrite alpha
            else:
                # Pen Logic: Normal drawing
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                # Ensure color is QColor
                pen = QPen(self.brushColor, self.brushSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            
            painter.setPen(pen)
            
            currentPoint = event.position().toPoint()
            painter.drawLine(self.lastPoint, currentPoint)
            self.lastPoint = currentPoint
            painter.end()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    # Tool Methods
    def set_tool_pen(self):
        self.eraserMode = False

    def set_tool_eraser(self):
        self.eraserMode = True

    def clear_canvas(self):
        self.image.fill(QColor(0, 0, 0, 1))
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.showFullScreen()
    sys.exit(app.exec())
