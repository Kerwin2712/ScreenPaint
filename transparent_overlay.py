import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QInputDialog
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QCursor
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QCursor
from PyQt6.QtWidgets import QFileDialog
from geometric_elements import PointObject, LineObject, CircleObject, RectangleObject
from capture_screen import take_screenshot
import copy

# --- Overlay Class ---

class TransparentOverlay(QWidget):
    interacted = pyqtSignal()
    crop_selected = pyqtSignal(QRect)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        
        # State
        self.image = QPixmap()
        self.objects = []
        
        # Undo/Redo Stacks
        self.undo_stack = []
        self.redo_stack = []
        
        self.lastPoint = QPoint()
        self.startPoint = QPoint()
        self.drawing = False
        
        # Line State
        self.pending_p1 = None
        self.press_pos = None
        
        # Parallel/Perp State
        self.selected_ref_line = None
        self.selected_through_point = None
        
        # Circle State
        self.compass_pts = [] 
        
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

    # Tool Slots
    def set_tool_pen(self): 
        self.currentTool = 'pen'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_eraser(self): 
        self.currentTool = 'eraser'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_line_segment(self): 
        self.currentTool = 'segment'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_line_ray(self): 
        self.currentTool = 'ray'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_line_infinite(self): 
        self.currentTool = 'line'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_line_horizontal(self):
        self.currentTool = 'hline'
        self.pending_p1 = None
        self._reset_tool_state()

    def set_tool_line_vertical(self):
        self.currentTool = 'vline'
        self.pending_p1 = None
        self._reset_tool_state()

    def set_tool_line_parallel(self):
        self.currentTool = 'parallel'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_line_perpendicular(self):
        self.currentTool = 'perpendicular'
        self.pending_p1 = None
        self._reset_tool_state()

    def set_tool_circle_radius(self):
        self.currentTool = 'circle_radius'
        self.pending_p1 = None
        self._reset_tool_state()

    def set_tool_circle_center_point(self):
        self.currentTool = 'circle_center_point'
        self.pending_p1 = None
        self._reset_tool_state()

    def set_tool_circle_compass(self):
        self.currentTool = 'circle_compass'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_point(self): 
        self.currentTool = 'point'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_hand(self): 
        self.currentTool = 'hand'
        self.pending_p1 = None
        self._reset_tool_state()
    
    def set_tool_rectangle(self):
        self.currentTool = 'rectangle'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_capture_crop(self):
        self.currentTool = 'capture_crop'
        self.pending_p1 = None
        self._reset_tool_state()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _reset_tool_state(self):
        self.selected_ref_line = None
        self.selected_through_point = None
        self.compass_pts = []
        self.drawing = False
        # Do not reset pending_p1 here usually, but slots do it.

    def save_state(self):
        # Deep copy to ensure independence
        state_objects = copy.deepcopy(self.objects)
        state_image = self.image.copy()
        self.undo_stack.append((state_objects, state_image))
        self.redo_stack.clear() # New action clears redo history

    def undo(self):
        if not self.undo_stack:
            return
        
        # Save current to Redo
        self.redo_stack.append((copy.deepcopy(self.objects), self.image.copy()))
        
        # Pop from Undo
        state_objects, state_image = self.undo_stack.pop()
        self.objects = state_objects
        self.image = state_image
        self.update()

    def redo(self):
        if not self.redo_stack:
            return
            
        # Save current to Undo
        self.undo_stack.append((copy.deepcopy(self.objects), self.image.copy()))
        
        # Pop from Redo
        state_objects, state_image = self.redo_stack.pop()
        self.objects = state_objects
        self.image = state_image
        self.update()

    def clear_canvas(self):
        self.save_state()
        self.image.fill(QColor(0, 0, 0, 1))
        self.objects.clear()
        self.pointIdCounter = 1
        self.pending_p1 = None
        self._reset_tool_state()
        self.update()

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
        
        # Draw Lines
        for obj in self.objects:
            if isinstance(obj, LineObject):
                obj.draw(painter, rect)

        # Draw Circles
        for obj in self.objects:
            if isinstance(obj, CircleObject):
                obj.draw(painter, rect)

        # Draw Points
        for obj in self.objects:
            if isinstance(obj, PointObject):
                obj.draw(painter, rect)
        
        # Draw Rectangles
        for obj in self.objects:
            if isinstance(obj, RectangleObject):
                obj.draw(painter, rect)
            
        # 3. Draw Preview
        self._draw_preview(painter)
        
        # 4. Draw Capture Selection
        if self.currentTool == 'capture_crop' and self.pending_p1:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            pen = QPen(Qt.GlobalColor.cyan, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 255, 255, 50))
            rect = QRect(self.pending_p1.pos(), mouse_pos).normalized()
            painter.drawRect(rect)

    def _draw_preview(self, painter):
        if self.currentTool in ['parallel', 'perpendicular']:
            self._draw_pp_preview(painter)
        elif self.currentTool in ['circle_center_point', 'circle_compass']:
            self._draw_circle_preview(painter)
        elif self.pending_p1 and self.currentTool in ['segment', 'ray', 'line']:
            self._draw_line_preview(painter)
        elif self.pending_p1 and self.currentTool == 'rectangle':
            self._draw_rect_preview(painter)

    def _draw_pp_preview(self, painter):
        if self.selected_ref_line:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            dummy_p1 = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
            temp_line = LineObject(dummy_p1, dummy_p1, self.currentTool, self.brushColor, self.brushSize, reference_line=self.selected_ref_line)
            temp_line.draw(painter, self.rect())

    def _draw_line_preview(self, painter):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        dummy_p2 = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
        temp_line = LineObject(self.pending_p1, dummy_p2, self.currentTool, self.brushColor, self.brushSize)
        temp_line.draw(painter, self.rect())

    def _draw_rect_preview(self, painter):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        p1 = self.pending_p1
        p3 = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
        
        # Construct vertices
        # p1 = (x1, y1), p3 = (x3, y3)
        # p2 = (x3, y1)
        # p4 = (x1, y3)
        
        x1, y1 = p1.x, p1.y
        x3, y3 = p3.x, p3.y
        
        p2 = PointObject(x3, y1, 0, size=0)
        p4 = PointObject(x1, y3, 0, size=0)
        
        temp_rect = RectangleObject(p1, p2, p3, p4, self.brushColor, self.brushSize)
        temp_rect.draw(painter, self.rect())

    def _draw_circle_preview(self, painter):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        
        if self.currentTool == 'circle_center_point' and self.pending_p1:
            dummy_p2 = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
            temp_circle = CircleObject(self.pending_p1, dummy_p2, 'center_point')
            temp_circle.draw(painter)
            
        elif self.currentTool == 'circle_compass' and len(self.compass_pts) == 2:
            dummy_center = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
            temp_circle = CircleObject(dummy_center, (self.compass_pts[0], self.compass_pts[1]), 'compass')
            temp_circle.draw(painter)

    def mousePressEvent(self, event):
        self.interacted.emit()
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.lastPoint = pos
            self.startPoint = pos 
            
            if self.currentTool == 'hand':
                # Hit detection: Points -> Lines -> Circles
                hit_obj = None
                for obj in reversed(self.objects):
                    if isinstance(obj, PointObject) and obj.contains(pos):
                        hit_obj = obj
                        break
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if (isinstance(obj, LineObject) or isinstance(obj, CircleObject)) and obj.contains(pos):
                            hit_obj = obj
                            break 
                if hit_obj:
                    self.draggingObject = hit_obj
                    self.lastDragPoint = pos
                    self.save_state() # Save before move
                    self.drawing = True
                return 

            if self.currentTool == 'eraser':
                self.drawing = True
                self.save_state() # Save before erase
                self._erase_objects_at(pos)
                return

            if self.currentTool == 'point': 
                self._create_point(pos)
                return
            
            # Circle Tools
            if self.currentTool == 'circle_radius':
                center = self._create_point(pos)
                
                # Use None as parent to be independent window
                # Ensure it is top-most
                dialog = QInputDialog() # No parent
                dialog.setWindowTitle("Radio")
                dialog.setLabelText("Ingrese el radio:")
                dialog.setDoubleValue(50)
                dialog.setDoubleMinimum(1)
                dialog.setDoubleMaximum(1000)
                dialog.setDoubleDecimals(1)
                # Force strictly on top
                dialog.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
                # Re-add frame hint if we want title bar, but maybe Frameless is safer if we want to ensure it pops over? 
                # Actually, standard Dialog title bar is fine.
                dialog.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                
                dialog.resize(300, 150)
                # Move to mouse pos?
                from PyQt6.QtGui import QCursor
                dialog.move(QCursor.pos())

                if dialog.exec():
                    self.save_state()
                    radius = dialog.doubleValue()
                    circle = CircleObject(center, radius, 'radius_num')
                    self.objects.append(circle)
                    self.update()
                
                # Bring UI back to top after dialog closes
                self.interacted.emit()
                return

            if self.currentTool == 'circle_center_point':
                hit_p = self._get_point_at(pos)
                if not hit_p:
                    hit_p = self._create_point(pos)
                    
                if not self.pending_p1:
                    self.pending_p1 = hit_p
                else:
                    self.save_state()
                    circle = CircleObject(self.pending_p1, hit_p, 'center_point')
                    self.objects.append(circle)
                    self.pending_p1 = None
                    self.update()
                return

            if self.currentTool == 'circle_compass':
                hit_p = self._get_point_at(pos)
                if not hit_p:
                    hit_p = self._create_point(pos)

                if len(self.compass_pts) < 2:
                    self.compass_pts.append(hit_p)
                else:
                    # Center
                    self.save_state()
                    circle = CircleObject(hit_p, (self.compass_pts[0], self.compass_pts[1]), 'compass')
                    self.objects.append(circle)
                    self.compass_pts = [] # Reset
                    self.update()
                return

            # Parallel / Perpendicular
            if self.currentTool in ['parallel', 'perpendicular']:
                hit_point = self._get_point_at(pos)
                hit_line = None
                if not hit_point:
                    for obj in reversed(self.objects):
                        if isinstance(obj, LineObject) and obj.contains(pos):
                            hit_line = obj
                            break
                
                if hit_line:
                    self.selected_ref_line = hit_line
                    if self.selected_through_point:
                        self._create_pp_line(self.selected_through_point, self.selected_ref_line)
                        self._reset_tool_state()
                    else:
                        self.drawing = True 

                elif hit_point:
                    self.selected_through_point = hit_point
                    if self.selected_ref_line:
                        self._create_pp_line(self.selected_through_point, self.selected_ref_line)
                        self._reset_tool_state()
                else:
                    # Empty space
                    if self.selected_ref_line:
                        p1 = self._create_point(pos)
                        self._create_pp_line(p1, self.selected_ref_line)
                        self._reset_tool_state()
                    elif self.selected_through_point:
                        pass
                    else:
                        p1 = self._create_point(pos)
                        self.selected_through_point = p1
                return

            if self.currentTool in ['segment', 'ray', 'line', 'hline', 'vline']:
                if self.currentTool in ['hline', 'vline']:
                    p1 = self._create_point(pos)
                    self._create_line_object(p1, p1) 
                    self.pending_p1 = None 
                else:
                    # Normal 2-point lines
                    self.press_pos = pos
                    hit_p = self._get_point_at(pos)
                    # Check for existing point to snap?
                    if not hit_p:
                        hit_p = self._create_point(pos)
                        
                    if not self.pending_p1:
                        self.pending_p1 = hit_p
                    else:
                        self._create_line_object(self.pending_p1, hit_p)
                        self.pending_p1 = None
                return
                    
            if self.currentTool == 'capture_crop':
                if not self.pending_p1:
                    self.pending_p1 = PointObject(pos.x(), pos.y(), 0, size=0)
                else:
                    # Second click completion
                    start_pos = self.pending_p1.pos()
                    rect = QRect(start_pos, pos).normalized()
                    self.pending_p1 = None
                    self.crop_selected.emit(rect)
                    self.update()
                return

            if self.currentTool == 'rectangle':
                # Similar logic to lines: Drag or Click-Click
                self.press_pos = pos
                hit_p = self._get_point_at(pos)
                if not hit_p: hit_p = self._create_point(pos)
                
                if not self.pending_p1:
                    self.pending_p1 = hit_p
                else:
                    self._create_rectangle(self.pending_p1, hit_p)
                return
            
            if self.currentTool == 'pen':
                self.drawing = True
                self.save_state()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        if self.drawing:
            if self.currentTool == 'pen':
                self._draw_freehand(pos)
                self.lastPoint = pos
            elif self.currentTool == 'eraser':
                self._erase_objects_at(pos)
            elif self.currentTool == 'hand' and self.draggingObject:
                # Drag logic
                dx = pos.x() - self.lastDragPoint.x()
                dy = pos.y() - self.lastDragPoint.y()
                self.draggingObject.move(dx, dy)
                self.lastDragPoint = pos
                self.update()
        else:
            # Update for preview drawing
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            
            if self.currentTool in ['segment', 'ray', 'line'] and self.pending_p1 and self.press_pos:
                drag_threshold = 5
                dist = (pos - self.press_pos).manhattanLength()
                
                if dist > drag_threshold:
                    hit_p = self._get_point_at(pos)
                    if not hit_p: hit_p = self._create_point(pos)
                    
                    self._create_line_object(self.pending_p1, hit_p)
                    self._create_line_object(self.pending_p1, hit_p)
                    self.pending_p1 = None

            if self.currentTool == 'rectangle' and self.pending_p1 and self.press_pos:
                drag_threshold = 5
                dist = (pos - self.press_pos).manhattanLength()
                
                if dist > drag_threshold:
                    hit_p = self._get_point_at(pos)
                    if not hit_p: hit_p = self._create_point(pos)
                    
                    self._create_rectangle(self.pending_p1, hit_p)

            if self.currentTool == 'capture_crop':
                if self.pending_p1:
                    start_pos = self.pending_p1.pos()
                    dist = (pos - start_pos).manhattanLength()
                    
                    if dist > 5:
                        rect = QRect(start_pos, pos).normalized()
                        self.pending_p1 = None
                        self.crop_selected.emit(rect)
                        self.update()
                    # If dist <= 5, we treat it as the first click of a 2-click selection
                self.drawing = False
                return

    def _get_point_at(self, pos):
        for obj in reversed(self.objects):
            if isinstance(obj, PointObject) and obj.contains(pos):
                return obj
        return None

    def _create_point(self, pos):
        self.save_state()
        new_point = PointObject(pos.x(), pos.y(), self.pointIdCounter)
        self.pointIdCounter += 1
        self.objects.append(new_point)
        self.update()
        return new_point
        
    def _create_line_object(self, p1_obj, p2_obj):
        self.save_state()
        new_line = LineObject(p1_obj, p2_obj, self.currentTool, self.brushColor, self.brushSize)
        self.objects.append(new_line)
        self.update()

    def _create_pp_line(self, p1, ref_line):
        self.save_state()
        new_line = LineObject(p1, p1, self.currentTool, self.brushColor, self.brushSize, reference_line=ref_line)
        self.objects.append(new_line)
        self.update()

    def _erase_objects_at(self, pos):
        to_remove = []
        for obj in self.objects:
            if obj.contains(pos):
                to_remove.append(obj)
        
        if not to_remove: return
        
        # Dependency check:
        # If Point is removed, Lines/Circles/Rectangles using it must go.
        # Simple recursive or iterative check.
        
        final_removal = set(to_remove)
        changed = True
        while changed:
            changed = False
            current_removals = list(final_removal)
            for obj in self.objects:
                if obj in final_removal: continue
                
                # Check dependencies
                if isinstance(obj, LineObject):
                    if obj.p1_obj in current_removals or (obj.p2_obj and obj.p2_obj in current_removals):
                        final_removal.add(obj)
                        changed = True
                elif isinstance(obj, CircleObject):
                    if obj.center_obj in current_removals:
                        final_removal.add(obj)
                        changed = True
                    # Check radius param dependencies if PointObject
                    if isinstance(obj.radius_param, PointObject) and obj.radius_param in current_removals:
                        final_removal.add(obj)
                        changed = True
                    # Compass list
                    if isinstance(obj.radius_param, tuple): 
                        if obj.radius_param[0] in current_removals or obj.radius_param[1] in current_removals:

                            final_removal.add(obj)
                            changed = True
                elif isinstance(obj, RectangleObject):
                    for p in obj.points:
                        if p in current_removals:
                            final_removal.add(obj)
                            changed = True

        self.objects = [obj for obj in self.objects if obj not in final_removal]
        self.update()

    def _draw_freehand(self, currentPoint):
        painter = QPainter(self.image)
        if self.currentTool == 'eraser':
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        else:
            painter.setPen(QPen(self.brushColor, self.brushSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        painter.drawLine(self.lastPoint, currentPoint)
        painter.end()
        self.update()

    def _create_rectangle(self, p1_obj, p3_obj):
        # p1 is TopLeft(ish), p3 is BottomRight(ish) - Diagrammatically
        # We need p2 and p4
        # p1 = (x1, y1), p3 = (x3, y3)
        # p2 = (x3, y1)
        # p4 = (x1, y3)
        
        # We only have p1 and p3 objects. 
        # Requirement: "cada vertice debe ser un punto nuevo" 
        # But wait, p1 and p3 MIGHT be existing points if the user clicked on them.
        # Should we use them directly as vertices? 
        # "al hacer dos clics se ponen dos puntos que formaran la diagonal"
        # "cada vertice debe ser un punto nuevo" implies the Corners are points.
        # It's ambiguous if the start/end *clics* are vertices themselves or if they just define position.
        # If I click an existing point, presumably I want that point to be a vertex.
        # So I will use p1_obj and p3_obj as 2 vertices.
        # I need to CREATE p2_obj and p4_obj.
        
        x1, y1 = p1_obj.pos().x(), p1_obj.pos().y()
        x3, y3 = p3_obj.pos().x(), p3_obj.pos().y()
        
        p2_obj = self._create_point(QPoint(x3, y1))
        p4_obj = self._create_point(QPoint(x1, y3))
        
        # Order: p1, p2, p3, p4
        self.save_state()
        new_rect = RectangleObject(p1_obj, p2_obj, p3_obj, p4_obj)
        self.objects.append(new_rect)
        self.pending_p1 = None
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.showFullScreen()
    sys.exit(app.exec())
