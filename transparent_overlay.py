import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap

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
        self.startPoint = QPoint() # For line tools
        self.drawing = False
        
        # Tools configuration
        # Tools: 'pen', 'eraser', 'segment', 'ray', 'line'
        self.currentTool = 'pen'
        self.brushSize = 3
        self.brushColor = Qt.GlobalColor.red
        self.eraserSize = 20

        # Initialize Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

    def resizeEvent(self, event):
        if self.image.isNull():
            self.image = QPixmap(self.size())
            self.image.fill(QColor(0, 0, 0, 1))
        else:
            new_image = QPixmap(self.size())
            new_image.fill(QColor(0, 0, 0, 1))
            painter = QPainter(new_image)
            painter.drawPixmap(0, 0, self.image)
            painter.end()
            self.image = new_image
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw committed content
        painter.drawPixmap(0, 0, self.image)
        
        # Draw preview for line tools
        if self.drawing and self.currentTool in ['segment', 'ray', 'line']:
            painter.setPen(QPen(self.brushColor, self.brushSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            
            p1 = self.startPoint
            p2 = self.lastPoint # Current mouse position
            
            start, end = self.calculate_line_geometry(p1, p2, self.currentTool)
            painter.drawLine(start, end)

    def calculate_line_geometry(self, p1, p2, tool_type):
        if tool_type == 'segment':
            return p1, p2
        
        # Important: QPoint coordinates
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return p1, p2

        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        # Helper to find intersection with screen bounds
        def get_intersections(x, y, dx, dy, forward_only=False):
            points = []
            # Intersect with Left (x=0)
            if dx != 0:
                y_at_0 = y + dy * (0 - x) / dx
                if 0 <= y_at_0 <= h:
                    if not forward_only or (0 - x) * dx >= 0: # Check direction
                        points.append(QPoint(0, int(y_at_0)))
            
            # Intersect with Right (x=w)
            if dx != 0:
                y_at_w = y + dy * (w - x) / dx
                if 0 <= y_at_w <= h:
                    if not forward_only or (w - x) * dx >= 0:
                        points.append(QPoint(w, int(y_at_w)))
            
            # Intersect with Top (y=0)
            if dy != 0:
                x_at_0 = x + dx * (0 - y) / dy
                if 0 <= x_at_0 <= w:
                    if not forward_only or (0 - y) * dy >= 0:
                        points.append(QPoint(int(x_at_0), 0))
            
            # Intersect with Bottom (y=h)
            if dy != 0:
                x_at_h = x + dx * (h - y) / dy
                if 0 <= x_at_h <= w:
                    if not forward_only or (h - y) * dy >= 0:
                        points.append(QPoint(int(x_at_h), h))
            
            return points

        if tool_type == 'ray':
            # From p1, go through p2 to edge
            # For ray, we just need one intersection in the direction of p2
            candidates = get_intersections(x1, y1, dx, dy, forward_only=True)
            # Find the farthest one (technically any boundary hit is "the end")
            # Usually there is only 1 valid boundary hit in that direction from inside.
            end_point = p2
            if candidates:
                # Prefer the one farthest from p1 to avoid 0-length glitches if near edge
                 end_point = max(candidates, key=lambda p: (p.x()-x1)**2 + (p.y()-y1)**2)
            return p1, end_point

        elif tool_type == 'line':
            # Through p1 and p2, extend both ways
            candidates = get_intersections(x1, y1, dx, dy, forward_only=False)
            if len(candidates) >= 2:
                # Find the two points farthest apart (points on boundary)
                # Sort by x then y
                candidates.sort(key=lambda p: (p.x(), p.y()))
                return candidates[0], candidates[-1]
            return p1, p2 # Fallback

        return p1, p2


    def mousePressEvent(self, event):
        self.interacted.emit()
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.lastPoint = event.position().toPoint()
            self.startPoint = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.drawing:
            currentPoint = event.position().toPoint()
            
            if self.currentTool in ['pen', 'eraser']:
                painter = QPainter(self.image)
                if self.currentTool == 'eraser':
                    pen = QPen(QColor(0, 0, 0, 1), self.eraserSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                else:
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                    pen = QPen(self.brushColor, self.brushSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                
                painter.setPen(pen)
                painter.drawLine(self.lastPoint, currentPoint)
                painter.end()
                self.lastPoint = currentPoint
                self.update() # Trigger repaint
            else:
                # Line tools: Just update 'lastPoint' for preview
                self.lastPoint = currentPoint
                self.update() # Trigger paintEvent to draw preview

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            # If line tool, commit the drawing now
            if self.currentTool in ['segment', 'ray', 'line']:
                painter = QPainter(self.image)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.setPen(QPen(self.brushColor, self.brushSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                
                start, end = self.calculate_line_geometry(self.startPoint, self.lastPoint, self.currentTool)
                painter.drawLine(start, end)
                painter.end()
                self.update()
            
            self.drawing = False

    # Tool Methods
    def set_tool_pen(self):
        self.currentTool = 'pen'

    def set_tool_eraser(self):
        self.currentTool = 'eraser'
        
    def set_tool_line_segment(self):
        self.currentTool = 'segment'
        
    def set_tool_line_ray(self):
        self.currentTool = 'ray'
        
    def set_tool_line_infinite(self):
        self.currentTool = 'line'

    def clear_canvas(self):
        self.image.fill(QColor(0, 0, 0, 1))
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.showFullScreen()
    sys.exit(app.exec())
