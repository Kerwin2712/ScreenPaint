import math
import copy
from PyQt6.QtCore import Qt, QPoint, QRect, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPolygon, QPainterPath, QPainterPathStroker

# --- Funciones auxiliares ---
def calculate_intersection(line1, line2):
    # Obtiene coordenadas de dos líneas para calcular su intersección
    
    def get_line_coords(line):
        p1 = line.p1_obj.pos()
        if line.p2_obj:
            p2 = line.p2_obj.pos()
        else:
            x1, y1 = p1.x(), p1.y()
            if line.type == 'hline': return x1, y1, x1+100, y1
            elif line.type == 'vline': return x1, y1, x1, y1+100
            elif line.type in ['parallel', 'perpendicular'] and line.reference_line:
                ref = line.reference_line
                rx1, ry1, rx2, ry2 = get_line_coords(ref)
                rdx, rdy = rx2 - rx1, ry2 - ry1
                if line.type == 'parallel':
                    return x1, y1, x1+rdx, y1+rdy
                else:
                    return x1, y1, x1-rdy, y1+rdx
            return x1, y1, x1+10, y1
            
        return p1.x(), p1.y(), p2.x(), p2.y()

    x1, y1, x2, y2 = get_line_coords(line1)
    x3, y3, x4, y4 = get_line_coords(line2)
    
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if denom == 0:
        return None  # Paralelas
        
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    
    x = x1 + ua * (x2 - x1)
    y = y1 + ua * (y2 - y1)
    
    return QPoint(int(x), int(y))

# --- Clases de figuras ---

class DrawingObject:
    def draw(self, painter, overlay_rect=None):
        raise NotImplementedError
    
    def contains(self, point, tolerance=None):
        return False
        
    def move(self, dx, dy):
        raise NotImplementedError

class PointObject(DrawingObject):
    def __init__(self, x, y, id_num, color=Qt.GlobalColor.red, size=4, parents=None):
        self.x = x
        self.y = y
        self.id = id_num
        self.color = color
        self.size = size
        self.parents = parents
        if self.parents:
            self.color = Qt.GlobalColor.gray
        
    def draw(self, painter, overlay_rect=None): 
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(QPoint(self.x, self.y), self.size, self.size)
        
        painter.setPen(Qt.GlobalColor.white)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
    def contains(self, point, tolerance=None):
        t = tolerance if tolerance is not None else self.size
        dx = point.x() - self.x
        dy = point.y() - self.y
        return (dx*dx + dy*dy) <= (t * t)

    def move(self, dx, dy):
        if self.parents:
            return  # Puntos dependientes no se pueden mover directamente
        self.x += dx
        self.y += dy

    def update(self):
        if self.parents and len(self.parents) == 2:
            l1, l2 = self.parents
            pt = calculate_intersection(l1, l2)
            if pt:
                self.x = pt.x()
                self.y = pt.y()
        
    def pos(self):
        return QPoint(self.x, self.y)

class LineObject(DrawingObject):
    def __init__(self, point_obj_1, point_obj_2, line_type, color=Qt.GlobalColor.blue, width=3, reference_line=None):
        self.p1_obj = point_obj_1
        self.p2_obj = point_obj_2
        self.type = line_type  # 'segment', 'ray', 'line', 'hline', 'vline', 'parallel', 'perpendicular'
        self.reference_line = reference_line
        self.color = color
        self.width = width
        
    def draw(self, painter, overlay_rect):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        start, end = self._calculate_geometry(overlay_rect)
        if start and end:
            painter.drawLine(start, end)
            
    def _calculate_geometry(self, rect):
        p1 = self.p1_obj.pos()
        x1, y1 = p1.x(), p1.y()
        w = rect.width()
        h = rect.height()

        def get_screen_intersections(x, y, dx, dy):
            points = []
            if dx == 0 and dy == 0: return []
            
            if dx != 0:
                y_at_0 = y + dy * (0 - x) / dx
                if 0 <= y_at_0 <= h: points.append(QPoint(0, int(y_at_0)))
            
            if dx != 0:
                y_at_w = y + dy * (w - x) / dx
                if 0 <= y_at_w <= h: points.append(QPoint(w, int(y_at_w)))
            
            if dy != 0:
                x_at_0 = x + dx * (0 - y) / dy
                if 0 <= x_at_0 <= w: points.append(QPoint(int(x_at_0), 0))
            
            if dy != 0:
                x_at_h = x + dx * (h - y) / dy
                if 0 <= x_at_h <= w: points.append(QPoint(int(x_at_h), h))
            
            points = sorted(list(set([(p.x(), p.y()) for p in points])))
            return [QPoint(*p) for p in points]


        if self.type == 'hline':
            return QPoint(0, y1), QPoint(w, y1)
        elif self.type == 'vline':
            return QPoint(x1, 0), QPoint(x1, h)
            
        elif self.type in ['parallel', 'perpendicular'] and self.reference_line:
            ref_p1 = self.reference_line.p1_obj.pos()
            ref_p2 = self.reference_line.p2_obj.pos()
            
            if self.reference_line.type == 'hline':
                ref_dx, ref_dy = 1, 0
            elif self.reference_line.type == 'vline':
                ref_dx, ref_dy = 0, 1
            elif self.reference_line.type in ['parallel', 'perpendicular']:
                ref_start, ref_end = self.reference_line._calculate_geometry(rect)
                ref_dx = ref_end.x() - ref_start.x()
                ref_dy = ref_end.y() - ref_start.y()
            else:    
                ref_dx = ref_p2.x() - ref_p1.x()
                ref_dy = ref_p2.y() - ref_p1.y()
                
            dx, dy = 0, 0
            if self.type == 'parallel':
                dx, dy = ref_dx, ref_dy
            else:
                dx, dy = -ref_dy, ref_dx
                
            intersections = get_screen_intersections(x1, y1, dx, dy)
            if len(intersections) >= 2:
                return intersections[0], intersections[-1]
            else:
                return QPoint(x1, y1), QPoint(x1+dx, y1+dy)
        
        p2 = self.p2_obj.pos() 
        x2, y2 = p2.x(), p2.y()
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return p1, p2

        def get_intersections_standard(x, y, dx, dy, forward_only=False):
            points = []
            if dx != 0:
                y_at_0 = y + dy * (0 - x) / dx
                if 0 <= y_at_0 <= h:
                    if not forward_only or (0 - x) * dx >= 0: points.append(QPoint(0, int(y_at_0)))
                y_at_w = y + dy * (w - x) / dx
                if 0 <= y_at_w <= h:
                    if not forward_only or (w - x) * dx >= 0: points.append(QPoint(w, int(y_at_w)))
            if dy != 0:
                x_at_0 = x + dx * (0 - y) / dy
                if 0 <= x_at_0 <= w:
                    if not forward_only or (0 - y) * dy >= 0: points.append(QPoint(int(x_at_0), 0))
                x_at_h = x + dx * (h - y) / dy
                if 0 <= x_at_h <= w:
                    if not forward_only or (h - y) * dy >= 0: points.append(QPoint(int(x_at_h), h))
            return points

        if self.type == 'segment':
            return p1, p2
        elif self.type == 'ray':
            candidates = get_intersections_standard(x1, y1, dx, dy, forward_only=True)
            end_point = p2
            if candidates:
                end_point = max(candidates, key=lambda p: (p.x()-x1)**2 + (p.y()-y1)**2)
            return p1, end_point
        elif self.type == 'line':
            candidates = get_intersections_standard(x1, y1, dx, dy, forward_only=False)
            if len(candidates) >= 2:
                candidates.sort(key=lambda p: (p.x(), p.y()))
                return candidates[-1], candidates[0]
            return p1, p2
        return p1, p2
        
    def contains(self, point, tolerance=None):
        p1 = self.p1_obj.pos()
        threshold = tolerance if tolerance is not None else 10
        x0, y0 = point.x(), point.y()
        x1, y1 = p1.x(), p1.y()

        if self.type == 'hline': return abs(y0 - y1) <= threshold
        elif self.type == 'vline': return abs(x0 - x1) <= threshold

        dx, dy = 0, 0
        has_direction = False
        
        if self.type in ['parallel', 'perpendicular'] and self.reference_line:
            ref_p1 = self.reference_line.p1_obj.pos()
            ref_p2 = self.reference_line.p2_obj.pos()
            
            ref_dx, ref_dy = 0, 0
            if self.reference_line.type == 'hline': ref_dx, ref_dy = 1, 0
            elif self.reference_line.type == 'vline': ref_dx, ref_dy = 0, 1
            else:
                ref_dx = ref_p2.x() - ref_p1.x()
                ref_dy = ref_p2.y() - ref_p1.y()
                
            if self.type == 'parallel':
                dx, dy = ref_dx, ref_dy
            else:
                dx, dy = -ref_dy, ref_dx
            has_direction = True
            
        elif self.p2_obj:
            p2 = self.p2_obj.pos()
            dx = p2.x() - x1
            dy = p2.y() - y1
            has_direction = True

        if not has_direction or (dx == 0 and dy == 0): return False
            
        A = -dy
        B = dx
        C = dy*x1 - dx*y1
        
        denom = math.sqrt(A*A + B*B)
        if denom == 0: return False
        
        dist = abs(A*x0 + B*y0 + C) / denom
        
        if dist > threshold: return False
            
        p1_to_pt_x = x0 - x1
        p1_to_pt_y = y0 - y1
        
        len_sq = dx*dx + dy*dy
        t = (p1_to_pt_x * dx + p1_to_pt_y * dy) / len_sq
        
        if self.type == 'segment': return 0 <= t <= 1
        elif self.type == 'ray': return t >= 0
        
        return True

    def move(self, dx, dy):
        self.p1_obj.move(dx, dy)
        if self.type not in ['hline', 'vline', 'parallel', 'perpendicular']:
            if self.p2_obj:
                self.p2_obj.move(dx, dy)

class CircleObject(DrawingObject):
    def __init__(self, center_point_obj, radius_param, circle_type='radius_num', color=Qt.GlobalColor.green, width=2, filled=False):
        self.center_obj = center_point_obj
        self.radius_param = radius_param 
        self.type = circle_type 
        self.color = color
        self.width = width
        self.filled = filled
    
    def get_radius(self):
        if self.type == 'radius_num':
            return float(self.radius_param)
        elif self.type == 'center_point':
            if isinstance(self.radius_param, PointObject):
                p_edge = self.radius_param.pos()
                center = self.center_obj.pos()
                return math.sqrt( (p_edge.x()-center.x())**2 + (p_edge.y()-center.y())**2 )
            return 10.0
        elif self.type == 'compass':
            pA = self.radius_param[0].pos()
            pB = self.radius_param[1].pos()
            return math.sqrt( (pB.x()-pA.x())**2 + (pB.y()-pA.y())**2 )
        return 10.0

    def draw(self, painter, overlay_rect=None):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine))
        if self.filled:
            color = QColor(self.color)
            color.setAlpha(50)
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        center = self.center_obj.pos()
        r = self.get_radius()
        
        painter.drawEllipse(center, int(r), int(r))

    def contains(self, point, tolerance=None):
        threshold = tolerance if tolerance is not None else 5
        
        center = self.center_obj.pos()
        r = self.get_radius()
        
        dist = math.sqrt( (point.x()-center.x())**2 + (point.y()-center.y())**2 )
        
        if self.filled:
            return dist <= r + threshold
        
        return abs(dist - r) <= threshold

    def move(self, dx, dy):
        self.center_obj.move(dx, dy)
        if self.type == 'center_point' and isinstance(self.radius_param, PointObject):
            self.radius_param.move(dx, dy)
        pass

class RectangleObject(DrawingObject):
    def __init__(self, p1_obj, p2_obj, p3_obj, p4_obj, color=Qt.GlobalColor.yellow, width=3, filled=False):
        self.points = [p1_obj, p2_obj, p3_obj, p4_obj]
        self.color = color
        self.width = width
        self.filled = filled
        self.rotation = 0
        
        p0_pos = p1_obj.pos()
        p2_pos = p3_obj.pos()
        self.original_half_width = abs(p2_pos.x() - p0_pos.x()) / 2
        self.original_half_height = abs(p2_pos.y() - p0_pos.y()) / 2
        
        self.original_center = QPointF(
            (p0_pos.x() + p2_pos.x()) / 2,
            (p0_pos.y() + p2_pos.y()) / 2
        )
    
    def draw(self, painter, overlay_rect=None):
        pen_width = 1 if self.filled else self.width
        painter.setPen(QPen(self.color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        if self.filled:
            fill_color = QColor(self.color)
            fill_color.setAlpha(100)
            painter.setBrush(fill_color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        pts = [p.pos() for p in self.points]
        painter.drawPolygon(pts)

    def contains(self, point, tolerance=None):
        threshold = tolerance if tolerance is not None else 10
        pos = point
        x0, y0 = pos.x(), pos.y()
        
        pts = [p.pos() for p in self.points]
        
        if self.filled:
            poly = QPolygon(pts)
            if poly.containsPoint(point, Qt.FillRule.OddEvenFill):
                return True
        
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i+1)%4]
            x1, y1 = p1.x(), p1.y()
            x2, y2 = p2.x(), p2.y()
            
            dx = x2 - x1
            dy = y2 - y1
            
            if dx == 0 and dy == 0: continue
            
            len_sq = dx*dx + dy*dy
            t = ((x0 - x1) * dx + (y0 - y1) * dy) / len_sq
            
            if 0 <= t <= 1:
                dist = abs(-dy*x0 + dx*y0 + dy*x1 - dx*y1) / math.sqrt(len_sq)
                if dist <= threshold:
                    return True
        return False

    def move(self, dx, dy):
        for p in self.points:
            p.move(dx, dy)
    
    def get_center(self):
        """Centro del rectángulo"""
        pts = [p.pos() for p in self.points]
        cx = sum(p.x() for p in pts) / 4
        cy = sum(p.y() for p in pts) / 4
        return QPointF(cx, cy)
    
    def get_rotation_handle_pos(self):
        """Posición del control de rotación (arriba-derecha)"""
        center = self.get_center()
        top_right = self.points[1].pos()
        handle_x = top_right.x() + 10
        handle_y = top_right.y() - 30
        return QPoint(int(handle_x), int(handle_y))
    
    def rotate(self, angle_degrees):
        """Rota el rectángulo por el ángulo dado alrededor de su centro"""
        import math
        
        self.rotation = angle_degrees
        
        center = self.get_center()
        cx, cy = center.x(), center.y()
        
        half_width = self.original_half_width
        half_height = self.original_half_height
        
        local_corners = [
            (-half_width, -half_height),
            (half_width, -half_height),
            (half_width, half_height),
            (-half_width, half_height)
        ]
        
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        for i, (lx, ly) in enumerate(local_corners):
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            
            new_x = cx + rotated_x
            new_y = cy + rotated_y
            
            self.points[i].x = int(new_x)
            self.points[i].y = int(new_y)

class FreehandObject(DrawingObject):
    def __init__(self, color=Qt.GlobalColor.black, width=3):
        self.path = QPainterPath()
        self.color = color
        self.width = width

    def __deepcopy__(self, memo):
        new_obj = FreehandObject(self.color, self.width)
        new_obj.path = QPainterPath(self.path)
        memo[id(self)] = new_obj
        return new_obj

    def draw(self, painter, overlay_rect=None):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path)

    def contains(self, point, tolerance=None):
        stroker = QPainterPathStroker()
        hit_width = self.width + (tolerance * 2 if tolerance is not None else 10)
        stroker.setWidth(hit_width)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        
        hit_path = stroker.createStroke(self.path)
        return hit_path.contains(QPointF(point))

    def move(self, dx, dy):
        from PyQt6.QtGui import QTransform
        transform = QTransform().translate(dx, dy)
        self.path = transform.map(self.path)


class TextObject(DrawingObject):
    def __init__(self, rect_corner1, rect_corner2, text, font_size=16, color=Qt.GlobalColor.black):
        self.rect_corner1 = QPoint(rect_corner1.x(), rect_corner1.y())
        self.rect_corner2 = QPoint(rect_corner2.x(), rect_corner2.y())
        self.text = text
        self.font_size = font_size
        self.color = color
    
    def get_rect(self):
        """Retorna el QRect normalizado del área de texto"""
        return QRect(self.rect_corner1, self.rect_corner2).normalized()
    
    def draw(self, painter, overlay_rect=None):
        rect = self.get_rect()
        
        painter.setPen(QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        
        painter.setPen(QPen(self.color, 1, Qt.PenStyle.SolidLine))
        font = QFont()
        font.setPixelSize(self.font_size)
        painter.setFont(font)
        
        text_rect = rect.adjusted(5, 5, -5, -5)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, self.text)
    
    def contains(self, point, tolerance=None):
        """Verifica si el punto está dentro del área de texto"""
        rect = self.get_rect()
        threshold = int(tolerance) if tolerance is not None else 10
        expanded_rect = rect.adjusted(-threshold, -threshold, threshold, threshold)
        return expanded_rect.contains(point)
    
    def contains_corner(self, point, tolerance=10):
        """Verifica si el punto está cerca de una esquina (para redimensionar)"""
        threshold = int(tolerance)
        
        corners = [
            self.rect_corner1,
            QPoint(self.rect_corner2.x(), self.rect_corner1.y()),
            self.rect_corner2,
            QPoint(self.rect_corner1.x(), self.rect_corner2.y())
        ]
        
        for i, corner in enumerate(corners):
            dx = abs(point.x() - corner.x())
            dy = abs(point.y() - corner.y())
            if dx <= threshold and dy <= threshold:
                return i
        
        return None
    
    def move(self, dx, dy):
        """Mueve el texto por el offset dado"""
        self.rect_corner1 = QPoint(self.rect_corner1.x() + dx, self.rect_corner1.y() + dy)
        self.rect_corner2 = QPoint(self.rect_corner2.x() + dx, self.rect_corner2.y() + dy)
