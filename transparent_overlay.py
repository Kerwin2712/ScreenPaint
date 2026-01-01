import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QInputDialog, QColorDialog
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QCursor, QPainterPath
from PyQt6.QtWidgets import QFileDialog
from geometric_elements import PointObject, LineObject, CircleObject, RectangleObject, FreehandObject, calculate_intersection
from capture_screen import take_screenshot
from preferences_manager import PreferencesManager
from preferences_dialog import PreferencesDialog
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
        # Removed WA_ShowWithoutActivating to allow keyboard shortcuts to work immediately
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
        self.pending_p1_created = False
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
        self.lastDragPoint = QPoint()
        # self.eraser_visual_path = QPainterPath() # Visual trail removed
        self.current_freehand_obj = None # Live pencil stroke
        
        # Copy/Paste Support
        self.clipboard = []  # Internal clipboard for copied objects
        self.selected_object = None  # Track last selected/interacted object
        self.pasting_preview = False  # True when showing paste preview
        self.paste_object = None  # Object being previewed for paste
        self.paste_offset = QPoint(0, 0)  # Offset from cursor to object origin
        
        # Rotation Support
        self.rotation_mode = False  # True when rotating a rectangle
        self.rotating_rectangle = None  # Rectangle being rotated
        self.rotation_start_angle = 0  # Initial angle when rotation started
        self.hovered_rectangle = None  # Rectangle currently under cursor
        
        # Keyboard Shortcuts
        self.preferences_manager = PreferencesManager()
        self.keyboard_shortcuts = self.preferences_manager.load_shortcuts()
        # Create reverse mapping: key_code -> tool_name
        self.key_to_tool = {key_code: tool for tool, (key_code, _) in self.keyboard_shortcuts.items()}


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
        self._update_eraser_cursor()

    def _update_eraser_cursor(self):
        # Create a circular cursor for the eraser
        pixmap_size = self.eraserSize + 2  # Slightly larger to avoid clipping
        pixmap = QPixmap(pixmap_size, pixmap_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle outline
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        center = pixmap_size // 2
        radius = self.eraserSize // 2
        painter.drawEllipse(QPoint(center, center), radius, radius)
        
        # Simple crosshair or dot in middle? maybe not needed for eraser
        painter.end()
        
        # Hotspot at center
        cursor = QCursor(pixmap, center, center)
        self.setCursor(cursor)

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

    def set_tool_rectangle_filled(self):
        self.currentTool = 'rectangle_filled'
        self._reset_tool_state()
        
    def set_tool_circle_radius(self):
        self.currentTool = 'circle_radius'
        self._reset_tool_state()

    def set_tool_circle_center_point(self):
        self.currentTool = 'circle_center_point'
        self._reset_tool_state()
        
    def set_tool_circle_filled(self):
        self.currentTool = 'circle_filled'
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

    def set_tool_rectangle_filled(self):
        self.currentTool = 'rectangle_filled'
        self.pending_p1 = None
        self._reset_tool_state()
        
    def set_tool_paint(self):
        # Open Color Dialog immediately when tool is selected
        # Use QColorDialog
        color = QColorDialog.getColor(self.brushColor, self, "Seleccionar Color")
        
        if color.isValid():
            self.brushColor = color
            self.currentTool = 'paint'
            self._reset_tool_state()
            # Change cursor to indicate paint mode?
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # If cancelled, maybe revert to previous tool or stay in paint but keep old color?
            # Let's stay in paint mode but keep old color if they just wanted to see the picker.
            # Or effectively do nothing if they cancelled the "Enter Paint Mode" action.
            # But they physically clicked the button.
            self.currentTool = 'paint' 
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
        self.setCursor(Qt.CursorShape.ArrowCursor) # Reset cursor by default
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
        
        rect = self.rect()
        
        # Draw pixmap (pencil strokes)
        if not self.image.isNull():
            painter.drawPixmap(0, 0, self.image)
        
        # Draw all objects
        for obj in self.objects:
            if isinstance(obj, PointObject):
                obj.draw(painter)
            elif isinstance(obj, LineObject):
                obj.draw(painter, self.rect())
            elif isinstance(obj, CircleObject):
                obj.draw(painter)
            elif isinstance(obj, RectangleObject):
                obj.draw(painter)
            elif isinstance(obj, FreehandObject):
                obj.draw(painter)
        
        # Draw live pencil stroke
        if self.current_freehand_obj:
            self.current_freehand_obj.draw(painter)
        
        # Draw preview elements for current tools
        if self.currentTool in ['segment', 'ray', 'line'] and self.pending_p1:
            self._draw_line_preview(painter)
        elif self.currentTool in ['rectangle', 'rectangle_filled'] and self.pending_p1:
            self._draw_rect_preview(painter)
        elif self.currentTool in ['circle_center_point', 'circle_filled', 'circle_compass']:
            self._draw_circle_preview(painter)
        elif self.currentTool in ['parallel', 'perpendicular']:
            self._draw_pp_preview(painter)
        
        # Draw paste preview with semi-transparency
        if self.pasting_preview and self.paste_object:
            painter.setOpacity(0.5)  # Semi-transparent
            
            if isinstance(self.paste_object, PointObject):
                self.paste_object.draw(painter)
            elif isinstance(self.paste_object, LineObject):
                self.paste_object.draw(painter, self.rect())
            elif isinstance(self.paste_object, CircleObject):
                self.paste_object.draw(painter)
            elif isinstance(self.paste_object, RectangleObject):
                self.paste_object.draw(painter)
            elif isinstance(self.paste_object, FreehandObject):
                self.paste_object.draw(painter)
            
            painter.setOpacity(1.0)  # Reset opacity
            
        # Draw Capture Selection
        if self.currentTool == 'capture_crop' and self.pending_p1:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            pen = QPen(Qt.GlobalColor.cyan, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 255, 255, 50))
            rect = QRect(self.pending_p1.pos(), mouse_pos).normalized()
            painter.drawRect(rect)
            
        # 5. Draw Eraser Visual Trail - REMOVED
        # if self.currentTool == 'eraser' and not self.eraser_visual_path.isEmpty():
        #     eraser_pen = QPen(QColor(200, 200, 200, 100), self.eraserSize, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        #     painter.setPen(eraser_pen)
        #     painter.setBrush(Qt.BrushStyle.NoBrush)
        #     painter.drawPath(self.eraser_visual_path)

    def _draw_preview(self, painter):
        if self.currentTool in ['parallel', 'perpendicular']:
            self._draw_pp_preview(painter)
        elif self.currentTool in ['circle_center_point', 'circle_compass', 'circle_filled']:
            self._draw_circle_preview(painter)
        elif self.pending_p1 and self.currentTool in ['segment', 'ray', 'line']:
            self._draw_line_preview(painter)
        elif self.pending_p1 and self.currentTool in ['rectangle', 'rectangle_filled']:
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
        
        filled = (self.currentTool == 'rectangle_filled')
        temp_rect = RectangleObject(p1, p2, p3, p4, self.brushColor, self.brushSize, filled=filled)
        temp_rect.draw(painter, self.rect())

    def _draw_circle_preview(self, painter):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        
        if self.currentTool in ['circle_center_point', 'circle_filled'] and self.pending_p1:
            dummy_p2 = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
            filled = (self.currentTool == 'circle_filled')
            temp_circle = CircleObject(self.pending_p1, dummy_p2, 'center_point', color=self.brushColor, width=self.brushSize, filled=filled)
            temp_circle.draw(painter)
            
        elif self.currentTool == 'circle_compass' and len(self.compass_pts) == 2:
            dummy_center = PointObject(mouse_pos.x(), mouse_pos.y(), 0, size=0)
            temp_circle = CircleObject(dummy_center, (self.compass_pts[0], self.compass_pts[1]), 'compass')
            temp_circle.draw(painter)

    def mousePressEvent(self, event):
        self.interacted.emit()
        
        # Handle paste preview mode
        if self.pasting_preview:
            if event.button() == Qt.MouseButton.LeftButton:
                # Finalize paste at current position
                pos = event.position().toPoint()
                self._finalize_paste(pos)
                return
            elif event.button() == Qt.MouseButton.RightButton:
                # Cancel paste
                self._cancel_paste_preview()
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.lastPoint = pos
            self.startPoint = pos 
            self.press_pos = pos
            
            if self.currentTool == 'hand':
                # Hit detection: Points -> Others
                hit_obj = None
                for obj in reversed(self.objects):
                    if isinstance(obj, PointObject) and obj.contains(pos):
                        hit_obj = obj
                        break
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if (isinstance(obj, LineObject) or isinstance(obj, CircleObject) or isinstance(obj, RectangleObject) or isinstance(obj, FreehandObject)) and obj.contains(pos):
                            hit_obj = obj
                            break
                if hit_obj:
                    self.draggingObject = hit_obj
                    self.selected_object = hit_obj  # Track for copy/paste
                    self.lastDragPoint = pos
                    self.save_state() # Save before move
                    self.drawing = True
                return

            if self.currentTool == 'eraser':
                self.drawing = True
                self.save_state() # Save before erase
                # self.eraser_visual_path = QPainterPath(QPointF(pos))
                # self.eraser_visual_path.moveTo(QPointF(pos))
                self._erase_objects_at(pos)
                # self._draw_freehand(pos) # Pixels no longer used for pencil
                return

            if self.currentTool == 'point': 
                # Check for intersections first
                intersection_point, parents = self._check_line_intersections(pos)
                if intersection_point:
                    self._create_point(intersection_point, parents=parents)
                else:
                    self._create_point(pos)
                return
            
            if self.currentTool == 'paint':
                # Hit detection
                hit_obj = None
                
                # Check points first (topmost)
                for obj in reversed(self.objects):
                    if isinstance(obj, PointObject) and obj.contains(pos):
                        hit_obj = obj
                        break
                
                # Then lines/circles/freehand
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if (isinstance(obj, LineObject) or isinstance(obj, CircleObject) or isinstance(obj, RectangleObject) or isinstance(obj, FreehandObject)) and obj.contains(pos):
                            hit_obj = obj
                            break 
                
                if hit_obj:
                    # Apply Color
                    self.save_state()
                    self.selected_object = hit_obj  # Track for copy/paste
                    hit_obj.color = self.brushColor
                    self._propagate_color_change(hit_obj)
                    self.update()
                
                # Do NOT open dialog on empty space click. 
                # User can click the toolbar button again to change color.
                return
            
                # Circle Tools
            if self.currentTool == 'circle_radius':
                center = self._create_point(pos, save_history=True)
                
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
                dialog.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                
                dialog.resize(300, 150)
                # Move to mouse pos?
                from PyQt6.QtGui import QCursor
                dialog.move(QCursor.pos())

                if dialog.exec():
                    # Do NOT save state here, we append to the state created by the point
                    radius = dialog.doubleValue()
                    circle = CircleObject(center, radius, 'radius_num', color=self.brushColor, width=self.brushSize)
                    self.objects.append(circle)
                    self.update()
                
                # Bring UI back to top after dialog closes
                self.interacted.emit()
                return

            if self.currentTool in ['circle_center_point', 'circle_filled']:
                hit_p = self._get_point_at(pos)
                
                if not self.pending_p1:
                    if not hit_p:
                        hit_p = self._create_point(pos, save_history=True)
                        self.pending_p1_created = True
                    else:
                        self.pending_p1_created = False
                    self.pending_p1 = hit_p
                else:
                    should_save = not self.pending_p1_created
                    if not hit_p:
                        hit_p = self._create_point(pos, save_history=should_save)
                        circle_save = False
                    else:
                        circle_save = should_save
                        
                    if circle_save: self.save_state()
                    
                    # Create Circle
                    filled = (self.currentTool == 'circle_filled')
                    circle = CircleObject(self.pending_p1, hit_p, 'center_point', color=self.brushColor, width=self.brushSize, filled=filled)
                    self.objects.append(circle)
                    self.pending_p1 = None
                    self.update()
                return

            if self.currentTool == 'circle_compass':
                hit_p = self._get_point_at(pos)
                
                save_this_step = False
                
                if not hit_p:
                    if len(self.compass_pts) == 0:
                        save_this_step = True # First point of the sequence
                    else:
                        save_this_step = False # Included in first point's history
                    
                    hit_p = self._create_point(pos, save_history=save_this_step)
                else:
                    # User clicked existing point
                    # If it's the first point of compass, we don't save history for the POINT, 
                    # but we haven't started a "transaction" if we just clicked an existing point.
                    # So dragging a compass from existing points might need its own save?
                    # Let's simplify: If we click existing point, we don't create new history entry YET.
                    # But if we complete the compass, we must ensure ONE history entry exists.
                    pass

                if len(self.compass_pts) < 2:
                    self.compass_pts.append(hit_p)
                else:
                    # Center
                    should_save = True
                    # If P1 or P2 were newly created, we reused their history.
                    # Ideally we want 1 entry. 
                    # If we created P1? Yes.
                    # IF we reused P1 and P2? Then we need to save now.
                    # Simpler heuristic: If objects changed since start of compass?
                    # Let's just FORCE save if we didn't just create a point with save=True.
                    # But verifying that is hard. 
                    # Let's use save_history=False for P3 (if created) effectively merging.
                    # If P3 was created, it "took" the history slot if we passed Save=False? No, create_point(False) appends to current.
                    
                    # We need to Ensure a Save happens if one hasn't happened yet.
                    # Let's assume P1 Creation triggers Save.
                    # If P1 existed, no Save.
                    # If P2 created? Save=False (merges).
                    # If P2 existed?
                    # If P3 created? Save=False.
                    
                    # WE ONLY need to explicitly save if ALL previous points were EXISTING points.
                    # How to track?
                    # Let's add a `compass_started_transaction` flag?
                    # Or just simple approach:
                    # If we create the Compass, we just call save_state() if we haven't modified objects list in this "action".
                    # But create_point modifies objects.
                    
                    # Robust approach: Always save at the END (Circle creation), and ensure intermediate points DID NOT save.
                    # P1: create(save=False).
                    # P2: create(save=False).
                    # P3: create(save=False).
                    # Circle: save=True.
                    # BUT: If user Undo after P1? They see nothing happened? That's weird. They should see P1.
                    # So P1 must save.
                    
                    # OK: P1 saves.
                    # P2 merges.
                    # P3 merges.
                    # Circle merges.
                    # If P1 was existing: P2 saves? 
                    # If P2 was existing: P3/Circle saves?
                    
                    # This implies state machine.
                    # Let's stick to: P1 creates History if new.
                    # If P1 existing, P2 creates History if new.
                    # If P2 existing, P3/Circle create History.
                    
                    # Determining if we SHOULD save for Circle:
                    # Check if we ALREADY pushed to history for this interaction? hard.
                    # Use a flag on logical state?
                    pass # Handled below

                    # Simplified Compass Logic for Unity
                    # If P3 is new, create it merging with previous.
                    # Circle merges with previous.
                    # BUT if P3 is existing, and P1/P2 were existing, we MUST save now.
                    
                    # Hack: Compare object count or use previous Save logic?
                    # Actually, since Compass involves distinct clicks, the user sees them as steps.
                    # Maybe it is OK if they are 3 Undo steps? 
                    # User request: "Group Undo Actions for Circle creation".
                    # So it SHOULD be 1 step.
                    
                    # Solution:
                    # On P1 click: If New, Save=True. Flag transaction_active=True.
                    # If Existing, transaction_active=False.
                    
                    # On P2 click: If New, Save=(not transaction_active). If saves, transaction_active=True.
                    
                    # On P3 click: If New, Save=(not transaction_active). If saves, transaction_active=True.
                    # Circle: Save=(not transaction_active).
                    
                    # Wait, where do we store `transaction_active` for Compass?
                    # `self.compass_pts` implies we are in compass mode.
                    # Add `self.compass_transaction_active` to class.
                    
                    if not self.compass_pts: # Start
                        self.compass_transaction_active = False

                    # P1 Logic handled above?
                    # We need to override the logic inside this block slightly.
                    pass
            
            if self.currentTool == 'circle_compass':
                hit_p = self._get_point_at(pos)
                
                # Determine if we are starting a sequence
                if len(self.compass_pts) == 0:
                    self.compass_transaction_active = False
                
                save_point = False
                if not hit_p:
                    # Attempting to create new point.
                    # Save only if we haven't already started a transaction
                    if not self.compass_transaction_active:
                        save_point = True
                        self.compass_transaction_active = True
                    hit_p = self._create_point(pos, save_history=save_point)
                
                if len(self.compass_pts) < 2:
                    self.compass_pts.append(hit_p)
                else:
                    # Center (P3)
                    # We already tried creating P3 above (hit_p).
                    
                    # Now create Circle
                    save_circle = False
                    if not self.compass_transaction_active:
                        save_circle = True
                        
                    if save_circle: self.save_state()
                    
                    circle = CircleObject(hit_p, (self.compass_pts[0], self.compass_pts[1]), 'compass', color=self.brushColor, width=self.brushSize)
                    self.objects.append(circle)
                    self.compass_pts = [] # Reset
                    self.compass_transaction_active = False # Reset
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
                    
                    if not self.pending_p1:
                        if not hit_p:
                            hit_p = self._create_point(pos, save_history=True)
                            self.pending_p1_created = True
                        else:
                            self.pending_p1_created = False # Existing point, history not consumed yet
                        self.pending_p1 = hit_p
                    else:
                        # Click-Click completion
                        should_save = not self.pending_p1_created
                        if not hit_p:
                            hit_p = self._create_point(pos, save_history=should_save)
                            line_save = False
                        else:
                            line_save = should_save
                        
                        self._create_line_object(self.pending_p1, hit_p, save_history=line_save)
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

            if self.currentTool in ['rectangle', 'rectangle_filled']:
                # Similar logic to lines: Drag or Click-Click
                self.press_pos = pos
                hit_p = self._get_point_at(pos)
                
                if not self.pending_p1:
                    if not hit_p: 
                        hit_p = self._create_point(pos, save_history=True)
                        self.pending_p1_created = True
                    else:
                        self.pending_p1_created = False
                    self.pending_p1 = hit_p
                else:
                    should_save = not self.pending_p1_created
                    if not hit_p: 
                        hit_p = self._create_point(pos, save_history=should_save)
                        rect_save = False
                    else:
                        rect_save = should_save
                        
                    self._create_rectangle(self.pending_p1, hit_p, filled=(self.currentTool == 'rectangle_filled'), save_history=rect_save)
                return
            
            if self.currentTool == 'pen':
                self.drawing = True
                # self.save_state() # Moved to release to avoid empty objects? 
                # Let's save on release or press. 
                # Actually, if we want undo to work for the whole stroke, we save on press.
                self.save_state()
                self.current_freehand_obj = FreehandObject(color=self.brushColor, width=self.brushSize)
                self.current_freehand_obj.path.moveTo(QPointF(pos))
                return

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        # Handle paste preview mode - update object position to follow cursor
        if self.pasting_preview and self.paste_object:
            # Calculate how much to move from current position to cursor
            if isinstance(self.paste_object, PointObject):
                dx = pos.x() - self.paste_object.x
                dy = pos.y() - self.paste_object.y
                self.paste_object.x = pos.x()
                self.paste_object.y = pos.y()
            else:
                # For complex objects, move them to follow cursor
                # Get a reference point (first point for lines/circles, corner for rectangles)
                if isinstance(self.paste_object, LineObject):
                    ref_x, ref_y = self.paste_object.p1_obj.x, self.paste_object.p1_obj.y
                    dx = pos.x() - ref_x
                    dy = pos.y() - ref_y
                elif isinstance(self.paste_object, CircleObject):
                    ref_x, ref_y = self.paste_object.center_obj.x, self.paste_object.center_obj.y
                    dx = pos.x() - ref_x
                    dy = pos.y() - ref_y
                elif isinstance(self.paste_object, RectangleObject):
                    ref_x, ref_y = self.paste_object.points[0].x, self.paste_object.points[0].y
                    dx = pos.x() - ref_x
                    dy = pos.y() - ref_y
                elif isinstance(self.paste_object, FreehandObject):
                    # For freehand, just move it by a small amount each time
                    # We'll use a simple approach
                    dx = pos.x() - self.paste_offset.x()
                    dy = pos.y() - self.paste_offset.y()
                    
                self.paste_object.move(dx, dy)
            
            self.paste_offset = pos
            self.update()
            return
        
        if self.drawing:
            if self.currentTool == 'pen':
                # self._draw_freehand(pos)
                if self.current_freehand_obj:
                    self.current_freehand_obj.path.lineTo(QPointF(pos))
                    self.update()
                self.lastPoint = pos
            elif self.currentTool == 'eraser':
                self._erase_objects_at(pos)
                # self.eraser_visual_path.lineTo(QPointF(pos)) # Removed visual trail

            elif self.currentTool == 'hand' and self.draggingObject:
                # Drag logic
                dx = pos.x() - self.lastDragPoint.x()
                dy = pos.y() - self.lastDragPoint.y()
                self.draggingObject.move(dx, dy)
                self.lastDragPoint = pos
                # Check for rectangle constraints if moving a point
                if isinstance(self.draggingObject, PointObject):
                    self._enforce_rectangle_constraints(self.draggingObject)
                    
                    # Logic: If moving a Center Point of a Circle, move the Perimeter Point too
                    # to keep the radius constant (Visual Move).
                    for obj in self.objects:
                        if isinstance(obj, CircleObject) and obj.type == 'center_point':
                            if obj.center_obj == self.draggingObject:
                                if isinstance(obj.radius_param, PointObject):
                                    obj.radius_param.move(dx, dy)
                                    
                self._propagate_changes()
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
                    should_save = not self.pending_p1_created
                    
                    if not hit_p: 
                        hit_p = self._create_point(pos, save_history=should_save)
                        line_save = False
                    else:
                        line_save = should_save
                    
                    self._create_line_object(self.pending_p1, hit_p, save_history=line_save)
                    self.pending_p1 = None

            if self.currentTool in ['rectangle', 'rectangle_filled'] and self.pending_p1 and self.press_pos:
                drag_threshold = 5
                dist = (pos - self.press_pos).manhattanLength()
                
                if dist > drag_threshold:
                    hit_p = self._get_point_at(pos)
                    should_save = not self.pending_p1_created
                    
                    if not hit_p: 
                        hit_p = self._create_point(pos, save_history=should_save)
                        rect_save = False
                    else:
                        rect_save = should_save
                    
                    self._create_rectangle(self.pending_p1, hit_p, filled=(self.currentTool == 'rectangle_filled'), save_history=rect_save)
            
            if self.currentTool in ['circle_center_point', 'circle_filled'] and self.pending_p1 and self.press_pos:
                drag_threshold = 5
                dist = (pos - self.press_pos).manhattanLength()
                
                if dist > drag_threshold:
                    hit_p = self._get_point_at(pos)
                    should_save = not self.pending_p1_created
                    
                    if not hit_p:
                        hit_p = self._create_point(pos, save_history=should_save)
                        circle_save = False
                    else:
                        circle_save = should_save
                        
                    if circle_save: self.save_state()
                    
                    filled = (self.currentTool == 'circle_filled')
                    circle = CircleObject(self.pending_p1, hit_p, 'center_point', color=self.brushColor, width=self.brushSize, filled=filled)
                    self.objects.append(circle)
                    self.pending_p1 = None
                    self.update()

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
            self.draggingObject = None

            if self.currentTool == 'pen' and self.current_freehand_obj:
                self.objects.append(self.current_freehand_obj)
                self.current_freehand_obj = None
                self.update()
            
            if self.currentTool == 'eraser':
                # self.eraser_visual_path = QPainterPath() # Clear trail
                self.update()

    def _get_point_at(self, pos):
        for obj in reversed(self.objects):
            if isinstance(obj, PointObject) and obj.contains(pos):
                return obj
        return None

        return None

    def _check_line_intersections(self, pos):
        # Brute force check all pairs of lines
        lines = [obj for obj in self.objects if isinstance(obj, LineObject)]
        threshold = 10
        
        for i in range(len(lines)):
            for j in range(i+1, len(lines)):
                l1 = lines[i]
                l2 = lines[j]
                
                pt = calculate_intersection(l1, l2)
                if pt:
                    # Check if click is near this intersection
                    dist = (QPoint(pt.x(), pt.y()) - pos).manhattanLength()
                    if dist <= threshold:
                        return QPoint(pt.x(), pt.y()), (l1, l2)
        return None, None

    def _create_point(self, pos, parents=None, color=None, save_history=True):
        if save_history: self.save_state()
        if color is None:
            color = self.brushColor
        new_point = PointObject(pos.x(), pos.y(), self.pointIdCounter, color=color, parents=parents)
        self.pointIdCounter += 1
        self.objects.append(new_point)
        self.update()
        return new_point

    def _enforce_rectangle_constraints(self, moved_point):
        for obj in self.objects:
            if isinstance(obj, RectangleObject):
                if moved_point in obj.points:
                    idx = obj.points.index(moved_point)
                    opp_idx = (idx + 2) % 4
                    next_idx = (idx + 1) % 4
                    prev_idx = (idx - 1) % 4
                    
                    opp_p = obj.points[opp_idx]
                    next_p = obj.points[next_idx]
                    prev_p = obj.points[prev_idx]
                    
                    # Logic assumes order P0(TL)->P1(TR)->P2(BR)->P3(BL) or similar cyclic
                    if idx % 2 == 0: # Even (0 or 2)
                        # Next shares Y with Moved, X with Opp
                        next_p.y = moved_point.y
                        next_p.x = opp_p.x
                        # Prev shares X with Moved, Y with Opp
                        prev_p.x = moved_point.x
                        prev_p.y = opp_p.y
                    else: # Odd (1 or 3)
                        # Next shares X with Moved, Y with Opp
                        next_p.x = moved_point.x
                        next_p.y = opp_p.y
                        # Prev shares Y with Moved, X with Opp
                        prev_p.y = moved_point.y
                        prev_p.x = opp_p.x
        
    def _create_line_object(self, p1_obj, p2_obj, save_history=True):
        if save_history: self.save_state()
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
        # Tolerance is radius of eraser
        tolerance = self.eraserSize / 2
        for obj in self.objects:
            if obj.contains(pos, tolerance=tolerance):
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

                    # Also remove points if Circle is removed?
                    if obj in current_removals:
                        final_removal.add(obj.center_obj)
                        if isinstance(obj.radius_param, PointObject):
                            final_removal.add(obj.radius_param)
                        if isinstance(obj.radius_param, tuple):
                            final_removal.add(obj.radius_param[0])
                            final_removal.add(obj.radius_param[1])
                            
                elif isinstance(obj, RectangleObject):
                    for p in obj.points:
                        if p in current_removals:
                            final_removal.add(obj)
                            changed = True
                elif isinstance(obj, PointObject):
                    # Check if it belongs to a Rectangle that is being removed
                    for rect in [r for r in current_removals if isinstance(r, RectangleObject)]:
                        if obj in rect.points:
                            final_removal.add(obj)
                            changed = True
                    # Check Circle dependencies for Points
                    for circ in [c for c in current_removals if isinstance(c, CircleObject)]:
                        if circ.center_obj == obj:
                            final_removal.add(obj)
                            changed = True
                        if isinstance(circ.radius_param, PointObject) and circ.radius_param == obj:
                            final_removal.add(obj)
                            changed = True
                        if isinstance(circ.radius_param, tuple) and obj in circ.radius_param:
                            final_removal.add(obj)
                            changed = True

                    # Check Line dependencies for Points
                    for line in [l for l in current_removals if isinstance(l, LineObject)]:
                        if line.p1_obj == obj or line.p2_obj == obj:
                            final_removal.add(obj)
                            changed = True
                            
                elif isinstance(obj, RectangleObject):
                    for p in obj.points:
                        if p in current_removals:
                            final_removal.add(obj)
                            changed = True
                elif isinstance(obj, PointObject):
                    # Check if it belongs to a Rectangle that is being removed
                    for rect in [r for r in current_removals if isinstance(r, RectangleObject)]:
                        if obj in rect.points:
                            final_removal.add(obj)
                            changed = True

        self.objects = [obj for obj in self.objects if obj not in final_removal]
        self.update()

    def _propagate_changes(self):
        # Update dependent objects
        # Currently only Points depend on Lines
        for obj in self.objects:
            if isinstance(obj, PointObject):
                # We need to call update. PointObject.update() handles the logic check.
                if hasattr(obj, 'update'):
                    obj.update()

    def _propagate_color_change(self, source_obj):
        if isinstance(source_obj, LineObject):
            source_obj.p1_obj.color = source_obj.color
            if source_obj.p2_obj and isinstance(source_obj.p2_obj, PointObject):
                source_obj.p2_obj.color = source_obj.color

        elif isinstance(source_obj, RectangleObject):
            for p in source_obj.points:
                p.color = source_obj.color
        elif isinstance(source_obj, CircleObject):
            source_obj.center_obj.color = source_obj.color
            if isinstance(source_obj.radius_param, PointObject):
                source_obj.radius_param.color = source_obj.color
            elif isinstance(source_obj.radius_param, tuple):
                source_obj.radius_param[0].color = source_obj.color
                source_obj.radius_param[1].color = source_obj.color

        elif isinstance(source_obj, PointObject):
            # Find rectangle
            for obj in self.objects:
                if isinstance(obj, RectangleObject) and source_obj in obj.points:
                    obj.color = source_obj.color
                    # Update all other points of this rect
                    for p in obj.points:
                        p.color = source_obj.color
                elif isinstance(obj, CircleObject):
                    # Check if point belongs to circle
                    is_part = False
                    if obj.center_obj == source_obj: is_part = True
                    if isinstance(obj.radius_param, PointObject) and obj.radius_param == source_obj: is_part = True
                    if isinstance(obj.radius_param, tuple) and source_obj in obj.radius_param: is_part = True
                    
                    if is_part:
                        obj.color = source_obj.color
                        # Propagate to other circle parts
                        obj.center_obj.color = source_obj.color
                        if isinstance(obj.radius_param, PointObject):
                            obj.radius_param.color = source_obj.color
                        elif isinstance(obj.radius_param, tuple):
                            obj.radius_param[0].color = source_obj.color
                            obj.radius_param[1].color = source_obj.color
                elif isinstance(obj, CircleObject):
                    # Check if point belongs to circle
                    is_part = False
                    if obj.center_obj == source_obj: is_part = True
                    if isinstance(obj.radius_param, PointObject) and obj.radius_param == source_obj: is_part = True
                    if isinstance(obj.radius_param, tuple) and source_obj in obj.radius_param: is_part = True
                    
                    if is_part:
                        obj.color = source_obj.color
                        # Propagate to other circle parts
                        obj.center_obj.color = source_obj.color
                        if isinstance(obj.radius_param, PointObject):
                            obj.radius_param.color = source_obj.color
                        elif isinstance(obj.radius_param, tuple):
                            obj.radius_param[0].color = source_obj.color
                            obj.radius_param[1].color = source_obj.color
                            
                elif isinstance(obj, LineObject):
                    if obj.p1_obj == source_obj or obj.p2_obj == source_obj:
                        obj.color = source_obj.color
                        # Propagate to other point
                        other_p = obj.p2_obj if obj.p1_obj == source_obj else obj.p1_obj
                        if isinstance(other_p, PointObject):
                            other_p.color = source_obj.color

    def _create_rectangle(self, p1_obj, p3_obj, filled=False, save_history=True):
        
        x1, y1 = p1_obj.pos().x(), p1_obj.pos().y()
        x3, y3 = p3_obj.pos().x(), p3_obj.pos().y()
        
        # Always create intermediate points WITHOUT saving history for them individually
        # as they are part of the rectangle action
        p2_obj = self._create_point(QPoint(x3, y1), save_history=False)
        p4_obj = self._create_point(QPoint(x1, y3), save_history=False)
        
        # Order: p1, p2, p3, p4
        if save_history: self.save_state()
        new_rect = RectangleObject(p1_obj, p2_obj, p3_obj, p4_obj, color=self.brushColor, width=self.brushSize, filled=filled)
        self.objects.append(new_rect)
        self.pending_p1 = None
        self.update()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for copy, paste, delete, undo/redo, rotation, and tool shortcuts"""
        key = event.key()
        
        # Check for tool shortcuts FIRST (before Ctrl combinations)
        # Only if no modifiers are pressed (except Shift/Alt which might be shortcuts themselves)
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if key in self.key_to_tool:
                tool_name = self.key_to_tool[key]
                self._activate_tool_shortcut(tool_name)
                event.accept()
                return
        
        # Ctrl+C: Copy
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._copy_selected_object()
            event.accept()
        
        # Ctrl+V: Activate paste preview mode
        elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._activate_paste_preview()
            event.accept()
        
        # Ctrl+Z: Undo
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.undo()
            event.accept()
        
        # Ctrl+Y: Redo
        elif event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redo()
            event.accept()
        
        # Escape: Cancel paste preview
        elif event.key() == Qt.Key.Key_Escape:
            if self.pasting_preview:
                self._cancel_paste_preview()
                event.accept()
            else:
                super().keyPressEvent(event)
        
        # Delete: Remove selected object
        elif event.key() == Qt.Key.Key_Delete:
            self._delete_selected_object()
            event.accept()
        
        # Left Arrow: Rotate selected rectangle counter-clockwise
        elif event.key() == Qt.Key.Key_Left:
            self._rotate_selected_rectangle(-5)  # Rotate -5 degrees
            event.accept()
        
        # Right Arrow: Rotate selected rectangle clockwise
        elif event.key() == Qt.Key.Key_Right:
            self._rotate_selected_rectangle(5)  # Rotate +5 degrees
            event.accept()
        
        else:
            super().keyPressEvent(event)
    
    def _copy_selected_object(self):
        """Copy the currently selected object to clipboard"""
        # Determine what to copy: draggingObject or selected_object
        obj_to_copy = self.draggingObject if self.draggingObject else self.selected_object
        
        if not obj_to_copy:
            # Try to get the last object in the list (most recently added)
            if self.objects:
                obj_to_copy = self.objects[-1]
        
        if obj_to_copy:
            try:
                # Deep copy the object and any related objects
                copied_obj = self._deep_copy_object(obj_to_copy)
                if copied_obj:
                    self.clipboard = [copied_obj]  # Store as list for future multi-select support
            except Exception as e:
                print(f"Error copying object: {e}")
    
    def _activate_paste_preview(self):
        """Activate paste preview mode - element follows cursor until click"""
        if not self.clipboard:
            return
        
        try:
            # Create a preview copy of the first object in clipboard
            obj = self.clipboard[0]
            self.paste_object = self._deep_copy_object(obj)
            
            if self.paste_object:
                self.pasting_preview = True
                # Calculate initial offset (center of object to cursor)
                self.paste_offset = QPoint(0, 0)
                self.setCursor(Qt.CursorShape.CrossCursor)
                self.update()
        except Exception as e:
            print(f"Error activating paste preview: {e}")
    
    def _cancel_paste_preview(self):
        """Cancel paste preview mode"""
        self.pasting_preview = False
        self.paste_object = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
    
    def _finalize_paste(self, pos):
        """Finalize paste at the given position"""
        if not self.paste_object:
            return
        
        self.save_state()  # Save for undo
        
        # Collect all objects that need to be added (object + dependencies)
        objects_to_add = self._collect_object_dependencies(self.paste_object)
        
        # Add all objects to the scene
        for obj in objects_to_add:
            self.objects.append(obj)
        
        # Exit preview mode
        self.pasting_preview = False
        self.paste_object = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
    
    def _delete_selected_object(self):
        """Delete the currently selected object"""
        obj_to_delete = self.draggingObject if self.draggingObject else self.selected_object
        
        if not obj_to_delete:
            return
        
        if obj_to_delete not in self.objects:
            return
        
        self.save_state()  # Save for undo
        
        # Use the existing erase logic which handles dependencies
        # Find a point on the object to use for erasure
        if isinstance(obj_to_delete, PointObject):
            erase_pos = QPoint(obj_to_delete.x, obj_to_delete.y)
        elif isinstance(obj_to_delete, LineObject):
            erase_pos = QPoint(obj_to_delete.p1_obj.x, obj_to_delete.p1_obj.y)
        elif isinstance(obj_to_delete, CircleObject):
            erase_pos = QPoint(obj_to_delete.center_obj.x, obj_to_delete.center_obj.y)
        elif isinstance(obj_to_delete, RectangleObject):
            erase_pos = QPoint(obj_to_delete.points[0].x, obj_to_delete.points[0].y)
        elif isinstance(obj_to_delete, FreehandObject):
            # For freehand, just remove it directly
            self.objects.remove(obj_to_delete)
            self.selected_object = None
            self.draggingObject = None
            self.update()
            return
        else:
            return
        
        # Erase with a small tolerance to ensure we hit the object
        self._erase_objects_at(erase_pos)
        
        self.selected_object = None
        self.draggingObject = None
        self.update()
    
    def _rotate_selected_rectangle(self, angle_increment):
        """Rotate the selected rectangle by the given angle increment"""
        obj_to_rotate = self.draggingObject if self.draggingObject else self.selected_object
        
        if not obj_to_rotate:
            return
        
        if not isinstance(obj_to_rotate, RectangleObject):
            return
        
        if obj_to_rotate not in self.objects:
            return
        
        self.save_state()  # Save for undo
        
        # Calculate new rotation angle
        new_angle = obj_to_rotate.rotation + angle_increment
        new_angle = new_angle % 360  # Normalize to 0-360 range
        
        # Call the rotate method which updates point positions
        obj_to_rotate.rotate(new_angle)
        
        self.update()
    
    def _activate_tool_shortcut(self, tool_name):
        """Activate a tool based on its name from keyboard shortcut"""
        tool_methods = {
            'pen': self.set_tool_pen,
            'hand': self.set_tool_hand,
            'point': self.set_tool_point,
            'segment': self.set_tool_line_segment,
            'circle_center_point': self.set_tool_circle_center_point,
            'rectangle': self.set_tool_rectangle,
            'eraser': self.set_tool_eraser,
            'paint': self.set_tool_paint,
        }
        
        if tool_name in tool_methods:
            tool_methods[tool_name]()
            # Ensure overlay keeps focus after changing tools
            self.setFocus()
            self.activateWindow()
    
    def _show_preferences(self):
        """Show the preferences dialog"""
        dialog = PreferencesDialog(self.keyboard_shortcuts, self)
        if dialog.exec() == PreferencesDialog.DialogCode.Accepted:
            # User saved changes, reload shortcuts
            self.keyboard_shortcuts = dialog.get_shortcuts()
            # Rebuild key->tool mapping
            self.key_to_tool = {key_code: tool for tool, (key_code, _) in self.keyboard_shortcuts.items()}
        
        # Return focus to overlay so keyboard shortcuts work immediately
        self.setFocus()
        self.activateWindow()
    
    def _deep_copy_object(self, obj):
        """Create a deep copy of a geometric object and all its dependencies
        Returns the copied object WITHOUT adding it or dependencies to self.objects
        """
        if isinstance(obj, PointObject):
            # Copy point
            new_point = PointObject(obj.x, obj.y, obj.id, color=obj.color, size=obj.size, parents=obj.parents)
            return new_point
        
        elif isinstance(obj, LineObject):
            # Copy the points first (without adding to objects)
            new_p1 = PointObject(obj.p1_obj.x, obj.p1_obj.y, self.pointIdCounter, color=obj.p1_obj.color, size=obj.p1_obj.size)
            new_p2 = None
            if obj.p2_obj:
                new_p2 = PointObject(obj.p2_obj.x, obj.p2_obj.y, self.pointIdCounter + 1, color=obj.p2_obj.color, size=obj.p2_obj.size)
            
            # Copy the line
            new_line = LineObject(new_p1, new_p2, obj.type, color=obj.color, width=obj.width, reference_line=obj.reference_line)
            return new_line
        
        elif isinstance(obj, CircleObject):
            # Copy center point
            new_center = PointObject(obj.center_obj.x, obj.center_obj.y, self.pointIdCounter, color=obj.center_obj.color, size=obj.center_obj.size)
            
            # Handle radius parameter based on circle type
            new_radius_param = obj.radius_param
            if obj.type == 'center_point' and isinstance(obj.radius_param, PointObject):
                new_radius_param = PointObject(obj.radius_param.x, obj.radius_param.y, self.pointIdCounter + 1, 
                color=obj.radius_param.color, size=obj.radius_param.size)
            elif obj.type == 'compass' and isinstance(obj.radius_param, tuple):
                p1 = PointObject(obj.radius_param[0].x, obj.radius_param[0].y, self.pointIdCounter + 1,
                color=obj.radius_param[0].color, size=obj.radius_param[0].size)
                p2 = PointObject(obj.radius_param[1].x, obj.radius_param[1].y, self.pointIdCounter + 2,
                color=obj.radius_param[1].color, size=obj.radius_param[1].size)
                new_radius_param = (p1, p2)
            
            # Copy the circle
            new_circle = CircleObject(new_center, new_radius_param, circle_type=obj.type, color=obj.color, width=obj.width, filled=obj.filled)
            return new_circle
        
        elif isinstance(obj, RectangleObject):
            # Copy all 4 corner points
            new_points = []
            for i, p in enumerate(obj.points):
                new_p = PointObject(p.x, p.y, self.pointIdCounter + i, color=p.color, size=p.size)
                new_points.append(new_p)
            
            # Copy the rectangle
            if len(new_points) == 4:
                new_rect = RectangleObject(new_points[0], new_points[1], new_points[2], new_points[3], 
                color=obj.color, width=obj.width, filled=obj.filled)
                return new_rect
        
        elif isinstance(obj, FreehandObject):
            # Use the existing __deepcopy__ implementation
            new_freehand = copy.deepcopy(obj)
            return new_freehand
        
        return None
    
    def _collect_object_dependencies(self, obj):
        """Collect all objects that should be added when finalizing paste
        Returns a list of all objects including the main object and its dependencies
        """
        objects_to_add = []
        
        if isinstance(obj, PointObject):
            objects_to_add.append(obj)
        
        elif isinstance(obj, LineObject):
            if obj.p1_obj:
                objects_to_add.append(obj.p1_obj)
                obj.p1_obj.id = self.pointIdCounter
                self.pointIdCounter += 1
            if obj.p2_obj:
                objects_to_add.append(obj.p2_obj)
                obj.p2_obj.id = self.pointIdCounter
                self.pointIdCounter += 1
            objects_to_add.append(obj)
        
        elif isinstance(obj, CircleObject):
            objects_to_add.append(obj.center_obj)
            obj.center_obj.id = self.pointIdCounter
            self.pointIdCounter += 1
            
            if obj.type == 'center_point' and isinstance(obj.radius_param, PointObject):
                objects_to_add.append(obj.radius_param)
                obj.radius_param.id = self.pointIdCounter
                self.pointIdCounter += 1
            elif obj.type == 'compass' and isinstance(obj.radius_param, tuple):
                objects_to_add.append(obj.radius_param[0])
                obj.radius_param[0].id = self.pointIdCounter
                self.pointIdCounter += 1
                objects_to_add.append(obj.radius_param[1])
                obj.radius_param[1].id = self.pointIdCounter
                self.pointIdCounter += 1
            
            objects_to_add.append(obj)
        
        elif isinstance(obj, RectangleObject):
            for p in obj.points:
                objects_to_add.append(p)
                p.id = self.pointIdCounter
                self.pointIdCounter += 1
            objects_to_add.append(obj)
        
        elif isinstance(obj, FreehandObject):
            objects_to_add.append(obj)
        
        return objects_to_add

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentOverlay()
    window.showFullScreen()
    sys.exit(app.exec())

