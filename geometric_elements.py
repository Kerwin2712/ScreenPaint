import math
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

# --- Helper Functions ---
def calculate_intersection(line1, line2):
    # Retrieve points defining the infinite lines
    # We need robust points. 
    # Use p1 and p2 (or calculated p2 for some types)
    
    def get_line_coords(line):
        p1 = line.p1_obj.pos()
        if line.p2_obj:
            p2 = line.p2_obj.pos()
        else:
            # Handle H/V/Parallel/Perp specially to get a second point
            # Mock screen rect for calculation? 
            # Or jus use slope logic directly?
            # Let's use slope logic.
            # But calculating slope requires logic similar to _calculate_geometry
            # Let's mock a second point based on type
            x1, y1 = p1.x(), p1.y()
            if line.type == 'hline': return x1, y1, x1+100, y1
            elif line.type == 'vline': return x1, y1, x1, y1+100
            elif line.type in ['parallel', 'perpendicular'] and line.reference_line:
                # Get ref slope
                ref = line.reference_line
                rx1, ry1, rx2, ry2 = get_line_coords(ref)
                rdx, rdy = rx2 - rx1, ry2 - ry1
                if line.type == 'parallel':
                    return x1, y1, x1+rdx, y1+rdy
                else: # Perp
                    return x1, y1, x1-rdy, y1+rdx
            # Fallback
            return x1, y1, x1+10, y1
            
        return p1.x(), p1.y(), p2.x(), p2.y()

    x1, y1, x2, y2 = get_line_coords(line1)
    x3, y3, x4, y4 = get_line_coords(line2)
    
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if denom == 0:
        return None # Parallel
        
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    
    # Intersection point
    x = x1 + ua * (x2 - x1)
    y = y1 + ua * (y2 - y1)
    
    return QPoint(int(x), int(y))

# --- Shape Classes ---

class DrawingObject:
    def draw(self, painter, overlay_rect=None):
        raise NotImplementedError
    
    def contains(self, point):
        return False
        
    def move(self, dx, dy):
        raise NotImplementedError

class PointObject(DrawingObject):
    def __init__(self, x, y, id_num, color=Qt.GlobalColor.red, size=10, parents=None):
        self.x = x
        self.y = y
        self.id = id_num
        self.color = color
        self.size = size # Radius
        self.parents = parents # Tuple/List of parent objects (e.g., 2 Lines)
        if self.parents:
            self.color = Qt.GlobalColor.gray # Distinguish dependent points?
        
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
        if self.parents:
            # Dependent points cannot be moved directly
            return
        self.x += dx
        self.y += dy

    def update(self):
        if self.parents and len(self.parents) == 2:
            # Assuming intersection of 2 lines for now
            l1, l2 = self.parents
            pt = calculate_intersection(l1, l2)
            if pt:
                self.x = pt.x()
                self.y = pt.y()
        
    def pos(self):
        return QPoint(self.x, self.y)

class LineObject(DrawingObject):
    def __init__(self, point_obj_1, point_obj_2, line_type, color=Qt.GlobalColor.blue, width=3, reference_line=None):
        self.p1_obj = point_obj_1 # PointObject
        self.p2_obj = point_obj_2 # PointObject (Can be None/Ignored for H/V/P/Perp)
        self.type = line_type # 'segment', 'ray', 'line', 'hline', 'vline', 'parallel', 'perpendicular'
        self.reference_line = reference_line # LineObject
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
        x1, y1 = p1.x(), p1.y()
        w = rect.width()
        h = rect.height()

        # Helper to get intersections for infinite lines defined by point (x,y) and slope (dx,dy)
        def get_screen_intersections(x, y, dx, dy):
            points = []
            if dx == 0 and dy == 0: return []
            
            # Intersect with Left (x=0)
            if dx != 0:
                y_at_0 = y + dy * (0 - x) / dx
                if 0 <= y_at_0 <= h: points.append(QPoint(0, int(y_at_0)))
            
            # Intersect with Right (x=w)
            if dx != 0:
                y_at_w = y + dy * (w - x) / dx
                if 0 <= y_at_w <= h: points.append(QPoint(w, int(y_at_w)))
            
            # Intersect with Top (y=0)
            if dy != 0:
                x_at_0 = x + dx * (0 - y) / dy
                if 0 <= x_at_0 <= w: points.append(QPoint(int(x_at_0), 0))
            
            # Intersect with Bottom (y=h)
            if dy != 0:
                x_at_h = x + dx * (h - y) / dy
                if 0 <= x_at_h <= w: points.append(QPoint(int(x_at_h), h))
            
            # Sort by x then y, return unique
            points = sorted(list(set([(p.x(), p.y()) for p in points])))
            return [QPoint(*p) for p in points]


        if self.type == 'hline':
            return QPoint(0, y1), QPoint(w, y1)
        elif self.type == 'vline':
            return QPoint(x1, 0), QPoint(x1, h)
            
        elif self.type in ['parallel', 'perpendicular'] and self.reference_line:
            # Parallel: Slope is same as reference line
            # Perpendicular: Slope is -1/m
            
            # Get Ref Slope
            ref_p1 = self.reference_line.p1_obj.pos()
            ref_p2 = self.reference_line.p2_obj.pos()
            
            # Special check if reference is hline/vline
            if self.reference_line.type == 'hline':
                ref_dx, ref_dy = 1, 0 # Horizontal
            elif self.reference_line.type == 'vline':
                ref_dx, ref_dy = 0, 1 # Vertical
            elif self.reference_line.type in ['parallel', 'perpendicular']:
                # Recursive logic? For simplicity, calculate its vector effectively
                # This could be complex. Let's assume ref is basic or handled by visual recursive calls?
                # Actually, simply getting p1 and p2 of the ref line object is risky if
                # the ref line is also infinite/parallel.
                # Better: calculate ref geometry first?
                # Simplified: Assume ref is defined by its p1/p2 objects which ALWAYS exist
                # ...Wait, for hline/vline, p2 might be dummy.
                # Let's enforce Ref Line has slope defined by its geometric calculation logic?
                # No, let's look at its type.
                
                # Simpler fallback: Calculate geometry of ref line.
                ref_start, ref_end = self.reference_line._calculate_geometry(rect)
                ref_dx = ref_end.x() - ref_start.x()
                ref_dy = ref_end.y() - ref_start.y()
            else:    
                ref_dx = ref_p2.x() - ref_p1.x()
                ref_dy = ref_p2.y() - ref_p1.y()
                
            dx, dy = 0, 0
            if self.type == 'parallel':
                dx, dy = ref_dx, ref_dy
            else: # perpendicular
                dx, dy = -ref_dy, ref_dx
                
            intersections = get_screen_intersections(x1, y1, dx, dy)
            if len(intersections) >= 2:
                # Return start and end (sorted in helper)
                return intersections[0], intersections[-1]
            else:
                # Fallback if exactly on edge or erratic
                return QPoint(x1, y1), QPoint(x1+dx, y1+dy)
        
        # Standard Line Logic
        p2 = self.p2_obj.pos() 
        x2, y2 = p2.x(), p2.y()
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return p1, p2

        def get_intersections_standard(x, y, dx, dy, forward_only=False):
            # Same as above but with direction check
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
                return candidates[-1], candidates[0] # Furthest points
            return p1, p2
        return p1, p2
        
    def contains(self, point):
        p1 = self.p1_obj.pos()
        threshold = 10
        x0, y0 = point.x(), point.y()
        x1, y1 = p1.x(), p1.y()

        if self.type == 'hline': return abs(y0 - y1) <= threshold
        elif self.type == 'vline': return abs(x0 - x1) <= threshold

        # For general lines, we need P2.
        # If Parallel/Perp, we might not have a stable P2 in self.p2_obj.
        # But we DO have a visual P2 if we calculate it. 
        # However, calculating it requires 'rect'.
        # Since 'contains' signature is fixed, we can't easily get 'rect'.
        # But we can approximate or rely on p2_obj if it exists.
        
        # If type is parallel/perp, we might have been initialized with p1=p2 (dummy).
        # In that case, we need to depend on the reference line slope.
        
        dx, dy = 0, 0
        has_direction = False
        
        if self.type in ['parallel', 'perpendicular'] and self.reference_line:
            # Calculate slope from reference
            ref_p1 = self.reference_line.p1_obj.pos()
            ref_p2 = self.reference_line.p2_obj.pos() # Might be dummy if ref is H/V
            
            ref_dx, ref_dy = 0, 0
            if self.reference_line.type == 'hline': ref_dx, ref_dy = 1, 0
            elif self.reference_line.type == 'vline': ref_dx, ref_dy = 0, 1
            else:
                ref_dx = ref_p2.x() - ref_p1.x()
                ref_dy = ref_p2.y() - ref_p1.y()
                
            if self.type == 'parallel':
                dx, dy = ref_dx, ref_dy
            else: # perpendicular
                dx, dy = -ref_dy, ref_dx
            has_direction = True
            
        elif self.p2_obj:
            p2 = self.p2_obj.pos()
            dx = p2.x() - x1
            dy = p2.y() - y1
            has_direction = True

        if not has_direction or (dx == 0 and dy == 0): return False
            
        # Distance from point to infinite line
        # |Ax + By + C| / sqrt(A^2 + B^2)
        # Line eq: -dy*x + dx*y + C = 0 -> A=-dy, B=dx
        # C = dy*x1 - dx*y1
        
        A = -dy
        B = dx
        C = dy*x1 - dx*y1
        
        denom = math.sqrt(A*A + B*B)
        if denom == 0: return False
        
        dist = abs(A*x0 + B*y0 + C) / denom
        
        if dist > threshold: return False
            
        # Check segment/ray bounds
        # Project t
        # t = ((P - P1) . (P2 - P1)) / |P2 - P1|^2
        # Here (dx, dy) represents (P2 - P1)
        
        p1_to_pt_x = x0 - x1
        p1_to_pt_y = y0 - y1
        
        len_sq = dx*dx + dy*dy
        t = (p1_to_pt_x * dx + p1_to_pt_y * dy) / len_sq
        
        if self.type == 'segment': return 0 <= t <= 1
        elif self.type == 'ray': return t >= 0
        
        # Line, HLine, VLine, Parallel, Perpendicular are infinite
        return True

    def move(self, dx, dy):
        self.p1_obj.move(dx, dy)
        if self.type not in ['hline', 'vline', 'parallel', 'perpendicular']:
            if self.p2_obj:
                self.p2_obj.move(dx, dy)

class CircleObject(DrawingObject):
    def __init__(self, center_point_obj, radius_param, circle_type='radius_num', color=Qt.GlobalColor.green, width=2):
        self.center_obj = center_point_obj # PointObject
        # radius_param can be:
        # - float (fixed number from input)
        # - PointObject (distance from center to this point defines radius)
        # - float (distance calculated from 2 other points for compass) - Compass logic usually results in fixed radius OR dependent on 2 other points.
        # Let's make it flexible.
        self.radius_param = radius_param 
        self.type = circle_type # 'radius_num', 'center_point' (radius from P2), 'compass' (radius from distance P2-P3, center at P1. Wait, Compass needs 2 points defining radius, then center.)
        # If 'compass', radius_param might be a simple value or a tuple of points?
        # User says: "Compas, hay que seleccionar 2 puntos y al hacer clic se crea un circulo con centro en el punto creado y el radio es la distacia entre los 2 puntos seleccionados"
        # So Compass Radius is CONSTANT distance between A and B at time of creation? Or Dynamic? 
        # Usually compass maintains distance. Moving A or B changes radius of circle at C. 
        # So radius_param for compass could be (PointA, PointB).
        
        self.color = color
        self.width = width
    
    def get_radius(self):
        if self.type == 'radius_num':
            return float(self.radius_param)
        elif self.type == 'center_point':
            # Distance between center and param point
            p_edge = self.radius_param.pos()
            center = self.center_obj.pos()
            return math.sqrt( (p_edge.x()-center.x())**2 + (p_edge.y()-center.y())**2 )
        elif self.type == 'compass':
            # radius_param is (PointA, PointB)
            pA = self.radius_param[0].pos()
            pB = self.radius_param[1].pos()
            return math.sqrt( (pB.x()-pA.x())**2 + (pB.y()-pA.y())**2 )
        return 10.0

    def draw(self, painter, overlay_rect=None):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        center = self.center_obj.pos()
        r = self.get_radius()
        
        painter.drawEllipse(center, int(r), int(r))

    def contains(self, point):
        # Hit detection: strictly on the rim? or inside? 
        # Usually rim for circles in geometry apps.
        threshold = 5
        
        center = self.center_obj.pos()
        r = self.get_radius()
        
        dist = math.sqrt( (point.x()-center.x())**2 + (point.y()-center.y())**2 )
        
        return abs(dist - r) <= threshold

    def move(self, dx, dy):
        # Moving circle moves its center.
        self.center_obj.move(dx, dy)
        # If 'center_point', moving circle (center) updates visual circle. Radius point stays?
        # If I move the circle, I usually expect the whole shape to translate.
        # But if it depends on other points...
        # If 'radius_num', simply moving center is fine.
        # If 'center_point', moving center changes radius if edge point is not moved.
        # To Move the strict circle, we just move center.
        # The user can move the defining points separately to reshape.
        pass

class RectangleObject(DrawingObject):
    def __init__(self, p1_obj, p2_obj, p3_obj, p4_obj, color=Qt.GlobalColor.yellow, width=3, filled=False):
        # Points should be ordered usually? Or just 4 points.
        # Let's assume they are passed in order: TopLeft, TopRight, BottomRight, BottomLeft
        # Or just 4 corners in any cyclic order.
        self.points = [p1_obj, p2_obj, p3_obj, p4_obj]
        self.color = color
        self.width = width
        self.filled = filled
    
    def draw(self, painter, overlay_rect=None):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        if self.filled:
            painter.setBrush(self.color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw 4 segments
        pts = [p.pos() for p in self.points]
        
        # Draw Polygon for filled shape
        painter.drawPolygon(pts)

    def contains(self, point):
        # Check distance to each of the 4 segments
        threshold = 10
        pos = point
        x0, y0 = pos.x(), pos.y()
        
        pts = [p.pos() for p in self.points]
        
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
            
            # Segment check
            if 0 <= t <= 1:
                # Perpendicular distance
                # |Ax + By + C| / sqrt(A^2+B^2)
                # -dy*x + dx*y + ...
                dist = abs(-dy*x0 + dx*y0 + dy*x1 - dx*y1) / math.sqrt(len_sq)
                if dist <= threshold:
                    return True
        return False

    def move(self, dx, dy):
        for p in self.points:
            p.move(dx, dy)

