import math
from PyQt6.QtCore import Qt, QPoint

# --- Shape Classes ---

class DrawingObject:
    def draw(self, painter, overlay_rect=None):
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
        
    def draw(self, painter, overlay_rect=None): 
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
        dx = point.x() - self.x
        dy = point.y() - self.y
        return (dx*dx + dy*dy) <= (self.size * self.size)

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        
    def pos(self):
        return QPoint(self.x, self.y)

class LineObject(DrawingObject):
    def __init__(self, point_obj_1, point_obj_2, line_type, color=Qt.GlobalColor.blue, width=3):
        self.p1_obj = point_obj_1 # PointObject
        self.p2_obj = point_obj_2 # PointObject
        self.type = line_type # 'segment', 'ray', 'line'
        self.color = color
        self.width = width
        
    def draw(self, painter, overlay_rect):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        # Use current positions of the point objects
        start, end = self._calculate_geometry(overlay_rect)
        if start and end:
            painter.drawLine(start, end)
            
    def _calculate_geometry(self, rect):
        p1 = self.p1_obj.pos()
        p2 = self.p2_obj.pos() # Used for direction or just as a second point reference
        x1, y1 = p1.x(), p1.y()
        
        # Override logic for forced horizontal/vertical
        if self.type == 'hline':
            # Horizontal Line: y is constant (y1), x goes from 0 to w
            return QPoint(0, y1), QPoint(rect.width(), y1)
        elif self.type == 'vline':
            # Vertical Line: x is constant (x1), y goes from 0 to h
            return QPoint(x1, 0), QPoint(x1, rect.height())
            
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
        p1 = self.p1_obj.pos()
        threshold = 10
        x0, y0 = point.x(), point.y()
        x1, y1 = p1.x(), p1.y()

        if self.type == 'hline':
            # Distance to horizontal line y = y1
            return abs(y0 - y1) <= threshold
        elif self.type == 'vline':
            # Distance to vertical line x = x1
            return abs(x0 - x1) <= threshold

        p2 = self.p2_obj.pos()
        x2, y2 = p2.x(), p2.y()
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0: return False
            
        A = -dy
        B = dx
        C = dy*x1 - dx*y1
        
        dist = abs(A*x0 + B*y0 + C) / math.sqrt(A*A + B*B)
        
        if dist > threshold: return False
            
        p1_to_pt_x = x0 - x1
        p1_to_pt_y = y0 - y1
        len_sq = dx*dx + dy*dy
        t = (p1_to_pt_x * dx + p1_to_pt_y * dy) / len_sq
        
        if self.type == 'segment': return 0 <= t <= 1
        elif self.type == 'ray': return t >= 0
        elif self.type == 'line': return True
        return False

    def move(self, dx, dy):
        # When moving the line, we move the associated points
        self.p1_obj.move(dx, dy)
        if self.type not in ['hline', 'vline']:
            self.p2_obj.move(dx, dy)
        # For H/V lines, do we move both points? 
        # Yes, moving the line implies translating it. Moving p1 is key.
        # But if we move HLine, p2 might be irrelevant or we just move visible line.
        # Actually hline/vline only depends on p1, p2 is just a placeholder or could be used for rotation later? 
        # For now, p1 defines the position (x1 for vline, y1 for hline).
        # So moving p1 is enough to move the infinite line. 
        # But to be consistent with "contains" and other logic, let's move both if present.
