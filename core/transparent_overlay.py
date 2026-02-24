import sys
import math
import copy
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QInputDialog, QColorDialog, QFileDialog
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QCursor, QPainterPath

# Imports actualizados a nuevas ubicaciones
from core.geometric_elements import (PointObject, LineObject, CircleObject,
                                     RectangleObject, FreehandObject, TextObject,
                                     calculate_intersection)
from tools.capture_screen import take_screenshot
from config.preferences_manager import PreferencesManager
from ui.preferences_dialog import PreferencesDialog
from ui.text_dialog import TextDialog


class TransparentOverlay(QWidget):
    interacted = pyqtSignal()
    crop_selected = pyqtSignal(QRect)
    minimize_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.image = QPixmap()
        self.objects = []
        
        self.undo_stack = []
        self.redo_stack = []
        
        self.lastPoint = QPoint()
        self.startPoint = QPoint()
        self.drawing = False
        
        self.pending_p1 = None
        self.pending_p1_created = False
        self.press_pos = None
        
        self.selected_ref_line = None
        self.selected_through_point = None
        
        self.compass_pts = [] 
        
        self.currentTool = 'pen'
        self.brushSize = 3
        self.brushColor = Qt.GlobalColor.red
        self.eraserSize = 20
        
        self.pointIdCounter = 1
        self.draggingObject = None
        self.lastDragPoint = QPoint()
        self.current_freehand_obj = None
        
        self.clipboard = []
        self.selected_object = None
        self.pasting_preview = False
        self.paste_object = None
        self.paste_offset = QPoint(0, 0)
        
        self.rotation_mode = False
        self.rotating_rectangle = None
        self.rotation_start_angle = 0
        self.hovered_rectangle = None
        
        self.preferences_manager = PreferencesManager()
        self.keyboard_shortcuts = self.preferences_manager.load_shortcuts()
        self.key_to_tool = {key_code: tool for tool, (key_code, _) in self.keyboard_shortcuts.items()}

        layout = QVBoxLayout()
        self.setLayout(layout)

    # ===== HERRAMIENTAS =====
    
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
        pixmap_size = self.eraserSize + 2
        pixmap = QPixmap(pixmap_size, pixmap_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        center = pixmap_size // 2
        radius = self.eraserSize // 2
        painter.drawEllipse(QPoint(center, center), radius, radius)
        painter.end()
        
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
        self.pending_p1 = None
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

    def set_tool_paint(self):
        color = QColorDialog.getColor(self.brushColor, self, "Seleccionar Color")
        if color.isValid():
            self.brushColor = color
        self.currentTool = 'paint'
        self._reset_tool_state()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def set_tool_text(self):
        self.currentTool = 'text'
        self.pending_p1 = None
        self._reset_tool_state()
        self.setCursor(Qt.CursorShape.IBeamCursor)
        
    def minimize_menu(self):
        self.minimize_requested.emit()

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
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ===== UNDO/REDO =====

    def save_state(self):
        state_objects = copy.deepcopy(self.objects)
        state_image = self.image.copy()
        self.undo_stack.append((state_objects, state_image))
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append((copy.deepcopy(self.objects), self.image.copy()))
        state_objects, state_image = self.undo_stack.pop()
        self.objects = state_objects
        self.image = state_image
        self.update()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append((copy.deepcopy(self.objects), self.image.copy()))
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

    # ===== EVENTOS DE RESIZE Y PAINT =====

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
        
        if not self.image.isNull():
            painter.drawPixmap(0, 0, self.image)
        
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
            elif isinstance(obj, TextObject):
                obj.draw(painter)
        
        if self.current_freehand_obj:
            self.current_freehand_obj.draw(painter)
        
        if self.currentTool in ['segment', 'ray', 'line'] and self.pending_p1:
            self._draw_line_preview(painter)
        elif self.currentTool in ['rectangle', 'rectangle_filled'] and self.pending_p1:
            self._draw_rect_preview(painter)
        elif self.currentTool in ['circle_center_point', 'circle_filled', 'circle_compass']:
            self._draw_circle_preview(painter)
        elif self.currentTool in ['parallel', 'perpendicular']:
            self._draw_pp_preview(painter)
        elif self.currentTool == 'text' and self.pending_p1:
            self._draw_text_preview(painter)
        
        if self.pasting_preview and self.paste_object:
            painter.setOpacity(0.5)
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
            elif isinstance(self.paste_object, TextObject):
                self.paste_object.draw(painter)
            painter.setOpacity(1.0)
            
        if self.currentTool == 'capture_crop' and self.pending_p1:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            pen = QPen(Qt.GlobalColor.cyan, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 255, 255, 50))
            rect = QRect(self.pending_p1.pos(), mouse_pos).normalized()
            painter.drawRect(rect)

    # ===== PREVIEWS =====

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
    
    def _draw_text_preview(self, painter):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        pen = QPen(self.brushColor, 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRect(self.pending_p1.pos(), mouse_pos).normalized()
        painter.drawRect(rect)

    # ===== EVENTOS DE RATÓN =====

    def mousePressEvent(self, event):
        self.interacted.emit()
        
        if self.pasting_preview:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                self._finalize_paste(pos)
                return
            elif event.button() == Qt.MouseButton.RightButton:
                self._cancel_paste_preview()
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.lastPoint = pos
            self.startPoint = pos 
            self.press_pos = pos
            
            if self.currentTool == 'hand':
                hit_obj = None
                resizing_text_corner = None
                
                for obj in reversed(self.objects):
                    if isinstance(obj, TextObject):
                        corner_idx = obj.contains_corner(pos, tolerance=15)
                        if corner_idx is not None:
                            hit_obj = obj
                            resizing_text_corner = corner_idx
                            break
                
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if isinstance(obj, PointObject) and obj.contains(pos):
                            hit_obj = obj
                            break
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if (isinstance(obj, LineObject) or isinstance(obj, CircleObject) or isinstance(obj, RectangleObject) or isinstance(obj, FreehandObject) or isinstance(obj, TextObject)) and obj.contains(pos):
                            hit_obj = obj
                            break
                if hit_obj:
                    self.draggingObject = hit_obj
                    self.selected_object = hit_obj
                    self.lastDragPoint = pos
                    self.save_state()
                    self.drawing = True
                    
                    if isinstance(hit_obj, TextObject) and resizing_text_corner is not None:
                        self.resizing_text_corner = resizing_text_corner
                    else:
                        self.resizing_text_corner = None
                return

            if self.currentTool == 'eraser':
                self.drawing = True
                self.save_state()
                self._erase_objects_at(pos)
                return

            if self.currentTool == 'point': 
                intersection_point, parents = self._check_line_intersections(pos)
                if intersection_point:
                    self._create_point(intersection_point, parents=parents)
                else:
                    self._create_point(pos)
                return
            
            if self.currentTool == 'paint':
                hit_obj = None
                for obj in reversed(self.objects):
                    if isinstance(obj, PointObject) and obj.contains(pos):
                        hit_obj = obj
                        break
                if not hit_obj:
                    for obj in reversed(self.objects):
                        if (isinstance(obj, LineObject) or isinstance(obj, CircleObject) or isinstance(obj, RectangleObject) or isinstance(obj, FreehandObject) or isinstance(obj, TextObject)) and obj.contains(pos):
                            hit_obj = obj
                            break 
                if hit_obj:
                    self.save_state()
                    self.selected_object = hit_obj
                    hit_obj.color = self.brushColor
                    self._propagate_color_change(hit_obj)
                    self.update()
                return
            
            if self.currentTool == 'circle_radius':
                center = self._create_point(pos, save_history=True)
                
                dialog = QInputDialog()
                dialog.setWindowTitle("Radio")
                dialog.setLabelText("Ingrese el radio:")
                dialog.setDoubleValue(50)
                dialog.setDoubleMinimum(1)
                dialog.setDoubleMaximum(1000)
                dialog.setDoubleDecimals(1)
                dialog.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                dialog.resize(300, 150)
                dialog.move(QCursor.pos())

                if dialog.exec():
                    radius = dialog.doubleValue()
                    circle = CircleObject(center, radius, 'radius_num', color=self.brushColor, width=self.brushSize)
                    self.objects.append(circle)
                    self.update()
                
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
                    
                    filled = (self.currentTool == 'circle_filled')
                    circle = CircleObject(self.pending_p1, hit_p, 'center_point', color=self.brushColor, width=self.brushSize, filled=filled)
                    self.objects.append(circle)
                    self.pending_p1 = None
                    self.update()
                return

            if self.currentTool == 'circle_compass':
                hit_p = self._get_point_at(pos)
                
                if len(self.compass_pts) == 0:
                    self.compass_transaction_active = False
                
                save_point = False
                if not hit_p:
                    if not self.compass_transaction_active:
                        save_point = True
                        self.compass_transaction_active = True
                    hit_p = self._create_point(pos, save_history=save_point)
                
                if len(self.compass_pts) < 2:
                    self.compass_pts.append(hit_p)
                else:
                    save_circle = False
                    if not self.compass_transaction_active:
                        save_circle = True
                        
                    if save_circle: self.save_state()
                    
                    circle = CircleObject(hit_p, (self.compass_pts[0], self.compass_pts[1]), 'compass', color=self.brushColor, width=self.brushSize)
                    self.objects.append(circle)
                    self.compass_pts = []
                    self.compass_transaction_active = False
                    self.update()
                return

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
                    start_pos = self.pending_p1.pos()
                    rect = QRect(start_pos, pos).normalized()
                    self.pending_p1 = None
                    self.crop_selected.emit(rect)
                    self.update()
                return

            if self.currentTool in ['rectangle', 'rectangle_filled']:
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
            
            if self.currentTool == 'text':
                self.press_pos = pos
                
                if not self.pending_p1:
                    self.pending_p1 = PointObject(pos.x(), pos.y(), 0, size=0)
                else:
                    corner2 = QPoint(pos.x(), pos.y())
                    
                    dialog = TextDialog(None, self.brushColor)
                    if dialog.exec():
                        text = dialog.get_text()
                        font_size = dialog.get_font_size()
                        color = dialog.get_color()
                        
                        if text.strip():
                            self.save_state()
                            text_obj = TextObject(self.pending_p1.pos(), corner2, text, font_size, color)
                            self.objects.append(text_obj)
                            self.update()
                    
                    self.pending_p1 = None
                    self.interacted.emit()
                return
            
            if self.currentTool == 'pen':
                self.drawing = True
                self.save_state()
                self.current_freehand_obj = FreehandObject(color=self.brushColor, width=self.brushSize)
                self.current_freehand_obj.path.moveTo(QPointF(pos))
                return

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        if self.pasting_preview and self.paste_object:
            if isinstance(self.paste_object, PointObject):
                self.paste_object.x = pos.x()
                self.paste_object.y = pos.y()
            else:
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
                    dx = pos.x() - self.paste_offset.x()
                    dy = pos.y() - self.paste_offset.y()
                    
                self.paste_object.move(dx, dy)
            
            self.paste_offset = pos
            self.update()
            return
        
        if self.drawing:
            if self.currentTool == 'pen':
                if self.current_freehand_obj:
                    self.current_freehand_obj.path.lineTo(QPointF(pos))
                    self.update()
                self.lastPoint = pos
            elif self.currentTool == 'eraser':
                self._erase_objects_at(pos)

            elif self.currentTool == 'hand' and self.draggingObject:
                if isinstance(self.draggingObject, TextObject) and self.resizing_text_corner is not None:
                    if self.resizing_text_corner == 0:
                        self.draggingObject.rect_corner1 = QPoint(pos.x(), pos.y())
                    elif self.resizing_text_corner == 2:
                        self.draggingObject.rect_corner2 = QPoint(pos.x(), pos.y())
                    elif self.resizing_text_corner == 1:
                        self.draggingObject.rect_corner1.setY(pos.y())
                        self.draggingObject.rect_corner2.setX(pos.x())
                    elif self.resizing_text_corner == 3:
                        self.draggingObject.rect_corner1.setX(pos.x())
                        self.draggingObject.rect_corner2.setY(pos.y())
                else:
                    dx = pos.x() - self.lastDragPoint.x()
                    dy = pos.y() - self.lastDragPoint.y()
                    self.draggingObject.move(dx, dy)
                
                self.lastDragPoint = pos
                if isinstance(self.draggingObject, PointObject):
                    self._enforce_rectangle_constraints(self.draggingObject)
                    for obj in self.objects:
                        if isinstance(obj, CircleObject) and obj.type == 'center_point':
                            if obj.center_obj == self.draggingObject:
                                if isinstance(obj.radius_param, PointObject):
                                    obj.radius_param.move(dx, dy)
                                    
                self._propagate_changes()
                self.update()
        else:
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
                
            self.drawing = False
            self.draggingObject = None

            if self.currentTool == 'pen' and self.current_freehand_obj:
                self.objects.append(self.current_freehand_obj)
                self.current_freehand_obj = None
                self.update()
            
            if self.currentTool == 'eraser':
                self.update()

    # ===== HELPERS INTERNOS =====

    def _get_point_at(self, pos):
        for obj in reversed(self.objects):
            if isinstance(obj, PointObject) and obj.contains(pos):
                return obj
        return None

    def _check_line_intersections(self, pos):
        lines = [obj for obj in self.objects if isinstance(obj, LineObject)]
        threshold = 10
        
        for i in range(len(lines)):
            for j in range(i+1, len(lines)):
                l1 = lines[i]
                l2 = lines[j]
                
                pt = calculate_intersection(l1, l2)
                if pt:
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
                    
                    if idx % 2 == 0:
                        next_p.y = moved_point.y
                        next_p.x = opp_p.x
                        prev_p.x = moved_point.x
                        prev_p.y = opp_p.y
                    else:
                        next_p.x = moved_point.x
                        next_p.y = opp_p.y
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
        tolerance = self.eraserSize / 2
        for obj in self.objects:
            if obj.contains(pos, tolerance=tolerance):
                to_remove.append(obj)
        
        if not to_remove: return
        
        final_removal = set(to_remove)
        changed = True
        while changed:
            changed = False
            current_removals = list(final_removal)
            for obj in self.objects:
                if obj in final_removal: continue
                
                if isinstance(obj, LineObject):
                    if obj.p1_obj in current_removals or (obj.p2_obj and obj.p2_obj in current_removals):
                        final_removal.add(obj)
                        changed = True
                elif isinstance(obj, CircleObject):
                    if obj.center_obj in current_removals:
                        final_removal.add(obj)
                        changed = True
                    if isinstance(obj.radius_param, PointObject) and obj.radius_param in current_removals:
                        final_removal.add(obj)
                        changed = True
                    if isinstance(obj.radius_param, tuple): 
                        if obj.radius_param[0] in current_removals or obj.radius_param[1] in current_removals:
                            final_removal.add(obj)
                            changed = True
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
                    for rect in [r for r in current_removals if isinstance(r, RectangleObject)]:
                        if obj in rect.points:
                            final_removal.add(obj)
                            changed = True
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
                    for line in [l for l in current_removals if isinstance(l, LineObject)]:
                        if line.p1_obj == obj or line.p2_obj == obj:
                            final_removal.add(obj)
                            changed = True

        self.objects = [obj for obj in self.objects if obj not in final_removal]
        self.update()

    def _propagate_changes(self):
        for obj in self.objects:
            if isinstance(obj, PointObject):
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
            for obj in self.objects:
                if isinstance(obj, RectangleObject) and source_obj in obj.points:
                    obj.color = source_obj.color
                    for p in obj.points:
                        p.color = source_obj.color
                elif isinstance(obj, CircleObject):
                    is_part = (obj.center_obj == source_obj or
                               (isinstance(obj.radius_param, PointObject) and obj.radius_param == source_obj) or
                               (isinstance(obj.radius_param, tuple) and source_obj in obj.radius_param))
                    if is_part:
                        obj.color = source_obj.color
                        obj.center_obj.color = source_obj.color
                        if isinstance(obj.radius_param, PointObject):
                            obj.radius_param.color = source_obj.color
                        elif isinstance(obj.radius_param, tuple):
                            obj.radius_param[0].color = source_obj.color
                            obj.radius_param[1].color = source_obj.color
                elif isinstance(obj, LineObject):
                    if obj.p1_obj == source_obj or obj.p2_obj == source_obj:
                        obj.color = source_obj.color
                        other_p = obj.p2_obj if obj.p1_obj == source_obj else obj.p1_obj
                        if isinstance(other_p, PointObject):
                            other_p.color = source_obj.color

    def _create_rectangle(self, p1_obj, p3_obj, filled=False, save_history=True):
        x1, y1 = p1_obj.pos().x(), p1_obj.pos().y()
        x3, y3 = p3_obj.pos().x(), p3_obj.pos().y()
        
        p2_obj = self._create_point(QPoint(x3, y1), save_history=False)
        p4_obj = self._create_point(QPoint(x1, y3), save_history=False)
        
        if save_history: self.save_state()
        new_rect = RectangleObject(p1_obj, p2_obj, p3_obj, p4_obj, color=self.brushColor, width=self.brushSize, filled=filled)
        self.objects.append(new_rect)
        self.pending_p1 = None
        self.update()

    # ===== ATAJOS DE TECLADO =====

    def keyPressEvent(self, event):
        key = event.key()
        
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if key in self.key_to_tool:
                tool_name = self.key_to_tool[key]
                self._activate_tool_shortcut(tool_name)
                event.accept()
                return
        
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._copy_selected_object()
            event.accept()
        elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._activate_paste_preview()
            event.accept()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.undo()
            event.accept()
        elif event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redo()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            if self.pasting_preview:
                self._cancel_paste_preview()
                event.accept()
            else:
                super().keyPressEvent(event)
        elif event.key() == Qt.Key.Key_Delete:
            self._delete_selected_object()
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            self._rotate_selected_rectangle(-5)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            self._rotate_selected_rectangle(5)
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def _copy_selected_object(self):
        obj_to_copy = self.draggingObject if self.draggingObject else self.selected_object
        if not obj_to_copy and self.objects:
            obj_to_copy = self.objects[-1]
        if obj_to_copy:
            try:
                copied_obj = self._deep_copy_object(obj_to_copy)
                if copied_obj:
                    self.clipboard = [copied_obj]
            except Exception as e:
                print(f"Error copying object: {e}")
    
    def _activate_paste_preview(self):
        if not self.clipboard:
            return
        try:
            obj = self.clipboard[0]
            self.paste_object = self._deep_copy_object(obj)
            if self.paste_object:
                self.pasting_preview = True
                self.paste_offset = QPoint(0, 0)
                self.setCursor(Qt.CursorShape.CrossCursor)
                self.update()
        except Exception as e:
            print(f"Error activating paste preview: {e}")
    
    def _cancel_paste_preview(self):
        self.pasting_preview = False
        self.paste_object = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
    
    def _finalize_paste(self, pos):
        if not self.paste_object:
            return
        self.save_state()
        objects_to_add = self._collect_object_dependencies(self.paste_object)
        for obj in objects_to_add:
            self.objects.append(obj)
        self.pasting_preview = False
        self.paste_object = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
    
    def _delete_selected_object(self):
        obj_to_delete = self.draggingObject if self.draggingObject else self.selected_object
        if not obj_to_delete or obj_to_delete not in self.objects:
            return
        self.save_state()
        if isinstance(obj_to_delete, PointObject):
            erase_pos = QPoint(obj_to_delete.x, obj_to_delete.y)
        elif isinstance(obj_to_delete, LineObject):
            erase_pos = QPoint(obj_to_delete.p1_obj.x, obj_to_delete.p1_obj.y)
        elif isinstance(obj_to_delete, CircleObject):
            erase_pos = QPoint(obj_to_delete.center_obj.x, obj_to_delete.center_obj.y)
        elif isinstance(obj_to_delete, RectangleObject):
            erase_pos = QPoint(obj_to_delete.points[0].x, obj_to_delete.points[0].y)
        elif isinstance(obj_to_delete, FreehandObject):
            self.objects.remove(obj_to_delete)
            self.selected_object = None
            self.draggingObject = None
            self.update()
            return
        else:
            return
        self._erase_objects_at(erase_pos)
        self.selected_object = None
        self.draggingObject = None
        self.update()
    
    def _rotate_selected_rectangle(self, angle_increment):
        obj_to_rotate = self.draggingObject if self.draggingObject else self.selected_object
        if not obj_to_rotate or not isinstance(obj_to_rotate, RectangleObject) or obj_to_rotate not in self.objects:
            return
        self.save_state()
        new_angle = (obj_to_rotate.rotation + angle_increment) % 360
        obj_to_rotate.rotate(new_angle)
        self.update()
    
    def _activate_tool_shortcut(self, tool_name):
        tool_methods = {
            'pen': self.set_tool_pen,
            'hand': self.set_tool_hand,
            'point': self.set_tool_point,
            'segment': self.set_tool_line_segment,
            'circle_center_point': self.set_tool_circle_center_point,
            'rectangle': self.set_tool_rectangle,
            'eraser': self.set_tool_eraser,
            'paint': self.set_tool_paint,
            'text': self.set_tool_text,
            'rectangle_filled': self.set_tool_rectangle_filled,
            'circle_filled': self.set_tool_circle_filled,
            'minimize': self.minimize_menu,
        }
        if tool_name in tool_methods:
            tool_methods[tool_name]()
            self.setFocus()
            self.activateWindow()
    
    def _show_preferences(self):
        dialog = PreferencesDialog(self.keyboard_shortcuts, self)
        if dialog.exec() == PreferencesDialog.DialogCode.Accepted:
            self.keyboard_shortcuts = dialog.get_shortcuts()
            self.key_to_tool = {key_code: tool for tool, (key_code, _) in self.keyboard_shortcuts.items()}
        self.setFocus()
        self.activateWindow()
    
    def _deep_copy_object(self, obj):
        if isinstance(obj, PointObject):
            return PointObject(obj.x, obj.y, obj.id, color=obj.color, size=obj.size, parents=obj.parents)
        elif isinstance(obj, LineObject):
            new_p1 = PointObject(obj.p1_obj.x, obj.p1_obj.y, self.pointIdCounter, color=obj.p1_obj.color, size=obj.p1_obj.size)
            new_p2 = None
            if obj.p2_obj:
                new_p2 = PointObject(obj.p2_obj.x, obj.p2_obj.y, self.pointIdCounter + 1, color=obj.p2_obj.color, size=obj.p2_obj.size)
            return LineObject(new_p1, new_p2, obj.type, color=obj.color, width=obj.width, reference_line=obj.reference_line)
        elif isinstance(obj, CircleObject):
            new_center = PointObject(obj.center_obj.x, obj.center_obj.y, self.pointIdCounter, color=obj.center_obj.color, size=obj.center_obj.size)
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
            return CircleObject(new_center, new_radius_param, circle_type=obj.type, color=obj.color, width=obj.width, filled=obj.filled)
        elif isinstance(obj, RectangleObject):
            new_points = [PointObject(p.x, p.y, self.pointIdCounter + i, color=p.color, size=p.size) for i, p in enumerate(obj.points)]
            if len(new_points) == 4:
                return RectangleObject(new_points[0], new_points[1], new_points[2], new_points[3], 
                color=obj.color, width=obj.width, filled=obj.filled)
        elif isinstance(obj, FreehandObject):
            return copy.deepcopy(obj)
        return None
    
    def _collect_object_dependencies(self, obj):
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
