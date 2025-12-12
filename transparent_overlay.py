import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont

# --- Shape Classes ---

class DrawingObject:
    def draw(self, painter):
        raise NotImplementedError
    
    def contains(self, point):
        return False
        
    def move(self, dx, dy):
        raise NotImplementedError

class PointObject(DrawingObject):
    def __init__(self, x, y, id_num, color=Qt.GlobalColor.red, size=10):
        self.x = x
        self.y = y
        self.id = id_num
        self.color = color
        self.size = size # Radius
        
    def draw(self, painter, overlay_rect=None): # overlay_rect is not used for PointObject but kept for consistent signature
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(QPoint(self.x, self.y), self.size, self.size)
        
        # Draw ID
        painter.setPen(Qt.GlobalColor.white)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(self.x - self.size, self.y - self.size, self.size*2, self.size*2), Qt.AlignmentFlag.AlignCenter, str(self.id))
        
    def contains(self, point):
        # Distance check
        dx = point.x() - self.x
        dy = point.y() - self.y
        return (dx*dx + dy*dy) <= (self.size * self.size)

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

class LineObject(DrawingObject):
    def __init__(self, p1, p2, line_type, color=Qt.GlobalColor.blue, width=3):
        self.p1 = p1 # QPoint
        self.p2 = p2 # QPoint (control point for direction)
        self.type = line_type # 'segment', 'ray', 'line'
        self.color = color
        self.width = width
        
        # Cache for hit detection (simplification: just check distance to segment formed by visible part?)
        # For infinite lines, this is tricky. We'll stick to the mathematical definition for 'contains'.
        
    def draw(self, painter, overlay_rect):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        start, end = self._calculate_geometry(overlay_rect)
        if start and end:
            painter.drawLine(start, end)
            # Store visible segment for hit detection if needed, or recompute
            
    def _calculate_geometry(self, rect):
        # Re-use the logic from TransparentOverlay, but encapsulated here or passed in?
        # Ideally logic should be here.
        # Duplicating logic for now to keep objects self-contained
        
        p1 = self.p1
        p2 = self.p2
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return p1, p2

        w = rect.width()
        h = rect.height()
        
        def get_intersections(x, y, dx, dy, forward_only=False):
            points = []
            if dx != 0:
                y_at_0 = y + dy * (0 - x) / dx
                if 0 <= y_at_0 <= h and (not forward_only or (0 - x) * dx >= 0): points.append(QPoint(0, int(y_at_0)))
                y_at_w = y + dy * (w - x) / dx
                if 0 <= y_at_w <= h and (not forward_only or (w - x) * dx >= 0): points.append(QPoint(w, int(y_at_w)))
            if dy != 0:
                x_at_0 = x + dx * (0 - y) / dy
                if 0 <= x_at_0 <= w and (not forward_only or (0 - y) * dy >= 0): points.append(QPoint(int(x_at_0), 0))
                x_at_h = x + dx * (h - y) / dy
                if 0 <= x_at_h <= w and (not forward_only or (h - y) * dy >= 0): points.append(QPoint(int(x_at_h), h))
            return points

        if self.type == 'segment':
            return p1, p2
        elif self.type == 'ray':
            candidates = get_intersections(x1, y1, dx, dy, forward_only=True)
            end_point = p2
            if candidates:
                end_point = max(candidates, key=lambda p: (p.x()-x1)**2 + (p.y()-y1)**2)
            return p1, end_point
        elif self.type == 'line':
            candidates = get_intersections(x1, y1, dx, dy, forward_only=False)
            if len(candidates) >= 2:
                candidates.sort(key=lambda p: (p.x(), p.y()))
                return candidates[0], candidates[-1]
            return p1, p2
        return p1, p2
        
    def contains(self, point):
        # Simplification: Distance to the line defined by p1, p2
        # BUT we need to respect the type (segment vs ray vs line)
        # Threshold
        threshold = 10
        
        x0, y0 = point.x(), point.y()
        x1, y1 = self.p1.x(), self.p1.y()
        x2, y2 = self.p2.x(), self.p2.y()
        
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return False # Point
            
        # Distance from point to infinite line
        # |Ax + By + C| / sqrt(A^2 + B^2)
        # Line eq: -dy*x + dx*y + C = 0
        # C = dy*x1 - dx*y1
        
        A = -dy
        B = dx
        C = dy*x1 - dx*y1
        
        dist = abs(A*x0 + B*y0 + C) / math.sqrt(A*A + B*B)
        
        if dist > threshold:
            return False
            
        # If it's close to the infinite line, check boundaries for segment/ray
        # Project point onto line to see if it falls within "segment" bounds
        # Dot product
        
        # Vector P1->Point
        p1_to_pt_x = x0 - x1
        p1_to_pt_y = y0 - y1
        
        # Vector P1->P2 (Direction)
        
        # For projection t:
        # P = P1 + t * (P2 - P1)
        # t = ( (Point - P1) . (P2 - P1) ) / |P2 - P1|^2
        
        len_sq = dx*dx + dy*dy
        t = (p1_to_pt_x * dx + p1_to_pt_y * dy) / len_sq
        
        if self.type == 'segment':
            return 0 <= t <= 1
        elif self.type == 'ray':
            return t >= 0
        elif self.type == 'line':
            return True # Already checked distance to infinite line
            
        return False

    def move(self, dx, dy):
        self.p1 += QPoint(dx, dy)
        self.p2 += QPoint(dx, dy)


# --- Overlay Class ---

class TransparentOverlay(QWidget):
    interacted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # State
        self.image = QPixmap() # Freehand layer
        self.objects = [] # List of DrawingObjects
        
        self.lastPoint = QPoint()
        self.startPoint = QPoint()
        self.drawing = False
        
        # Tools: 'pen', 'eraser', 'segment', 'ray', 'line', 'point', 'hand'
        self.currentTool = 'pen'
        self.brushSize = 3
        self.brushColor = Qt.GlobalColor.red
        self.eraserSize = 20
        
        self.pointIdCounter = 1
        self.draggingObject = None
        self.lastDragPoint = QPoint()

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Draw Freehand Layer
        painter.drawPixmap(0, 0, self.image)
        
        # 2. Draw Objects
        rect = self.rect()
        for obj in self.objects:
            obj.draw(painter, rect if isinstance(obj, LineObject) else None)
            
        # 3. Draw Preview
        if self.drawing and self.currentTool in ['segment', 'ray', 'line']:
            self._draw_line_preview(painter)

    def _draw_line_preview(self, painter):
        # Create a temporary object just for consistent drawing logic or draw manually
        # Re-using the class logic is better but we don't have an object yet.
        # Let's create a temp object
        temp_line = LineObject(self.startPoint, self.lastPoint, self.currentTool, self.brushColor, self.brushSize)
        temp_line.draw(painter, self.rect())

    def mousePressEvent(self, event):
        self.interacted.emit()
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.lastPoint = pos
            self.startPoint = pos
            
            if self.currentTool == 'hand':
                # Hit detection (Top to Bottom visually -> Reverse list)
                for obj in reversed(self.objects):
                    if obj.contains(pos):
                        self.draggingObject = obj
                        self.lastDragPoint = pos
                        self.drawing = True
                        break
            elif self.currentTool == 'point':
                # Create Point immediately
                new_point = PointObject(pos.x(), pos.y(), self.pointIdCounter)
                self.pointIdCounter += 1
                self.objects.append(new_point)
                self.update()
            else:
                self.drawing = True

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.drawing:
            if self.currentTool == 'hand' and self.draggingObject:
                dx = pos.x() - self.lastDragPoint.x()
                dy = pos.y() - self.lastDragPoint.y()
                self.draggingObject.move(dx, dy)
                self.lastDragPoint = pos
                self.update()
                
            elif self.currentTool in ['pen', 'eraser']:
                self._draw_freehand(pos)
                
            elif self.currentTool in ['segment', 'ray', 'line']:
                self.lastPoint = pos
                self.update() # Update preview

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.drawing:
                if self.currentTool in ['segment', 'ray', 'line']:
                    # Commit Line Object
                    # Don't create if points are same (click)
                    if self.startPoint != self.lastPoint:
                       new_line = LineObject(self.startPoint, self.lastPoint, self.currentTool, self.brushColor, self.brushSize)
                       self.objects.append(new_line)
                       self.update()
                
                self.drawing = False
                self.draggingObject = None

    def _draw_freehand(self, currentPoint):
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
        self.update()

    # Tool Slots
    def set_tool_pen(self): self.currentTool = 'pen'
    def set_tool_eraser(self): self.currentTool = 'eraser'
    def set_tool_line_segment(self): self.currentTool = 'segment'
    def set_tool_line_ray(self): self.currentTool = 'ray'
    def set_tool_line_infinite(self): self.currentTool = 'line'
    def set_tool_point(self): self.currentTool = 'point'
    def set_tool_hand(self): self.currentTool = 'hand'

    def clear_canvas(self):
        self.image.fill(QColor(0, 0, 0, 1))
        self.objects.clear()
        self.pointIdCounter = 1
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.showFullScreen()
    sys.exit(app.exec())
