import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont
from geometric_elements import PointObject, LineObject

# --- Overlay Class ---

class TransparentOverlay(QWidget):
    interacted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True) # Enable for 2-click preview
        
        # State
        self.image = QPixmap() # Freehand layer
        self.objects = [] # List of DrawingObjects
        
        self.lastPoint = QPoint()
        self.startPoint = QPoint()
        self.drawing = False
        
        # Creating Line State
        self.pending_p1 = None # PointObject if waiting for P2
        self.press_pos = None # To detect drag vs click
        
        # Tools
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
        # Draw Lines first so Points appear on top
        rect = self.rect()
        
        # Filter and draw Lines
        for obj in self.objects:
            if isinstance(obj, LineObject):
                obj.draw(painter, rect)

        # Filter and draw Points
        for obj in self.objects:
            if isinstance(obj, PointObject):
                # Pass rect just in case, though ignored
                obj.draw(painter, rect)
            
        # 3. Draw Preview
        if self.pending_p1:
            # Create a temp line using pending P1 and current mouse pos
            # Use cursor pos from mapFromGlobal or last tracked pos
            from PyQt6.QtGui import QCursor # Import here or top
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            # To create a temp line object, we need a "PointObject" for the cursor?
            # Or just manually draw for preview to avoid ID spam
            
            # Manually draw preview using LineObject logic would be cleaner but complex to reuse.
            # Create a valid LineObject with a dummy P2
            dummy_p2 = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
            temp_line = LineObject(self.pending_p1, dummy_p2, self.currentTool, self.brushColor, self.brushSize)
            temp_line.draw(painter, rect)

    def mousePressEvent(self, event):
        self.interacted.emit()
        from PyQt6.QtGui import QCursor # Import here or top
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.lastPoint = pos
            self.startPoint = pos # Freehand uses this
            
            if self.currentTool == 'hand':
                # Hit detection: Prioritize Points over Lines
                hit_obj = None
                
                # Check Points first (Top-most first if multiple)
                for obj in reversed(self.objects):
                    if isinstance(obj, PointObject) and obj.contains(pos):
                        hit_obj = obj
                        break
                
                # If no Point hit, check Lines
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if isinstance(obj, LineObject) and obj.contains(pos):
                            hit_obj = obj
                            break
                            
                if hit_obj:
                    self.draggingObject = hit_obj
                    self.lastDragPoint = pos
                    self.drawing = True
                        
            elif self.currentTool == 'point':
                self._create_point(pos)
                
            elif self.currentTool == 'eraser':
                self.drawing = True
                self._erase_objects_at(pos)
                
            elif self.currentTool in ['segment', 'ray', 'line', 'hline', 'vline']:
                # Dual Mode Logic
                # For hline/vline, ideally we just need ONE click (the point it passes through).
                # But to maintain consistency, let's stick to the P1 establishment.
                # Actually, for horizontal/vertical, user clicks a point and that's it?
                # User request: "pasen por un punto". Just 1 point is needed.
                
                if self.currentTool in ['hline', 'vline']:
                    # Single click creation for H/V lines? Or create a point?
                    # Let's create P1 at click, and immediately create the line.
                    p1 = self._create_point(pos)
                    # For consistency with LineObject structure requiring 2 points (though 2nd unused for logic):
                    self._create_line_object(p1, p1) # Same point or dummy
                    self.pending_p1 = None # Should not be pending
                    
                else:
                    # Normal 2-point lines
                    self.press_pos = pos
                    if not self.pending_p1:
                        # First Click/Press: Create P1
                        self.pending_p1 = self._create_point(pos)
                    else:
                        # Second Click (if doing 2-click method and we are here)
                        # Create P2 and connect
                        p2 = self._create_point(pos)
                        self._create_line_object(self.pending_p1, p2)
                        self.pending_p1 = None
                    
            elif self.currentTool == 'pen':
                self.drawing = True

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        if self.pending_p1:
            # We are in "Waiting for P2" mode (either Dragging or Hovering)
            self.update() # Repaint preview
        
        if (event.buttons() & Qt.MouseButton.LeftButton):
            if self.currentTool == 'hand' and self.draggingObject:
                dx = pos.x() - self.lastDragPoint.x()
                dy = pos.y() - self.lastDragPoint.y()
                self.draggingObject.move(dx, dy)
                self.lastDragPoint = pos
                self.update()
                
            elif self.currentTool == 'pen' and self.drawing:
                self._draw_freehand(pos)

            elif self.currentTool == 'eraser' and self.drawing:
                self._draw_freehand(pos)
                self._erase_objects_at(pos)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            
            if self.currentTool in ['segment', 'ray', 'line'] and self.pending_p1 and self.press_pos:
                # Check for Drag vs Click
                drag_threshold = 5
                dist = (pos - self.press_pos).manhattanLength()
                
                if dist > drag_threshold:
                    # It was a Drag -> Finish line now
                    p2 = self._create_point(pos)
                    self._create_line_object(self.pending_p1, p2)
                    self.pending_p1 = None
                else:
                    # It was a Click -> Do nothing, keep pending_p1, wait for 2nd click
                    pass
            
            self.drawing = False
            self.draggingObject = None

    def _create_point(self, pos):
        new_point = PointObject(pos.x(), pos.y(), self.pointIdCounter)
        self.pointIdCounter += 1
        self.objects.append(new_point)
        self.update()
        return new_point
        
    def _create_line_object(self, p1_obj, p2_obj):
        new_line = LineObject(p1_obj, p2_obj, self.currentTool, self.brushColor, self.brushSize)
        self.objects.append(new_line)
        self.update()

    def _erase_objects_at(self, pos):
        # Remove objects at pos. 
        # If Point is removed, remove coupled Lines.
        
        to_remove = []
        # Find hits
        for obj in self.objects:
            if obj.contains(pos):
                to_remove.append(obj)
                
        # If nothing to remove, done
        if not to_remove: return
        
        # Determine dependent lines to remove
        final_removal = set(to_remove)
        
        # Iterate to find lines connected to points in to_remove
        # Repeat until stable? Or just one pass? One pass is enough if we check all lines
        for obj in self.objects:
            if isinstance(obj, LineObject):
                if obj.p1_obj in to_remove or obj.p2_obj in to_remove:
                    final_removal.add(obj)
        
        # Rebuild list
        self.objects = [obj for obj in self.objects if obj not in final_removal]
        self.update()

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
    def set_tool_pen(self): 
        self.currentTool = 'pen'
        self.pending_p1 = None
        
    def set_tool_eraser(self): 
        self.currentTool = 'eraser'
        self.pending_p1 = None
        
    def set_tool_line_segment(self): 
        self.currentTool = 'segment'
        self.pending_p1 = None
        
    def set_tool_line_ray(self): 
        self.currentTool = 'ray'
        self.pending_p1 = None
        
    def set_tool_line_infinite(self): 
        self.currentTool = 'line'
        self.pending_p1 = None
        
    def set_tool_line_horizontal(self):
        self.currentTool = 'hline'
        self.pending_p1 = None

    def set_tool_line_vertical(self):
        self.currentTool = 'vline'
        self.pending_p1 = None
        
    def set_tool_point(self): 
        self.currentTool = 'point'
        self.pending_p1 = None
        
    def set_tool_hand(self): 
        self.currentTool = 'hand'
        self.pending_p1 = None

    def clear_canvas(self):
        self.image.fill(QColor(0, 0, 0, 1))
        self.objects.clear()
        self.pointIdCounter = 1
        self.pending_p1 = None
        self.update()
        
from PyQt6.QtGui import QCursor # Ensure import

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.showFullScreen()
    sys.exit(app.exec())
