import math
import copy
from PyQt6.QtCore import Qt, QPoint, QRect, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPolygon, QPainterPath, QPainterPathStroker

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
        # painter.drawText(QRect(self.x - self.size, self.y - self.size, self.size*2, self.size*2), Qt.AlignmentFlag.AlignCenter, str(self.id))
        
    def contains(self, point, tolerance=None):
        t = tolerance if tolerance is not None else self.size
        dx = point.x() - self.x
        dy = point.y() - self.y
        return (dx*dx + dy*dy) <= (t * t)

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
        
    def contains(self, point, tolerance=None):
        p1 = self.p1_obj.pos()
        threshold = tolerance if tolerance is not None else 10
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
    def __init__(self, center_point_obj, radius_param, circle_type='radius_num', color=Qt.GlobalColor.green, width=2, filled=False):
        self.center_obj = center_point_obj # PointObject
        self.radius_param = radius_param 
        self.type = circle_type 
        self.color = color
        self.width = width
        self.filled = filled
    
    def get_radius(self):
        if self.type == 'radius_num':
            return float(self.radius_param)
        elif self.type == 'center_point':
            # Distance between center and param point
            if isinstance(self.radius_param, PointObject):
                p_edge = self.radius_param.pos()
                center = self.center_obj.pos()
                return math.sqrt( (p_edge.x()-center.x())**2 + (p_edge.y()-center.y())**2 )
            return 10.0
        elif self.type == 'compass':
            # radius_param is (PointA, PointB)
            pA = self.radius_param[0].pos()
            pB = self.radius_param[1].pos()
            return math.sqrt( (pB.x()-pA.x())**2 + (pB.y()-pA.y())**2 )
        return 10.0

    def draw(self, painter, overlay_rect=None):
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine))
        if self.filled:
            color = QColor(self.color)
            color.setAlpha(50) # Translucent fill
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
        # If defined by a point (not fixed number), move that point too
        # so radius remains constant
        if self.type == 'center_point' and isinstance(self.radius_param, PointObject):
            self.radius_param.move(dx, dy)
        elif self.type == 'compass' and isinstance(self.radius_param, (list, tuple)):
            # For compass, radius is usually fixed distance between A and B ??
            # Or does the circle effectively own the "radius"?
            # Actually, if it's a 'compass' circle created at C with radius |AB|,
            # usually A and B are independent. Moving the circle C shouldn't move A and B.
            # But it implies the circle at C is just a "stamp" of that radius.
            # However, since we don't carry A and B with the circle in the current impl (we might be storing ref?),
            # let's check init. Confirmed: self.radius_param stored as tuple of points?
            # Re-reading my previous edit: circle = CircleObject(hit_p, (pA, pB), 'compass'...)
            # So yes.
            # If I move the circle, do I change the radius definition?
            # User expectation: "Move the circle".
            # If I move C, and A/B stay, radius |AB| stays. So circle size stays.
            # So I ONLY move C.
            pass
        # Moving circle moves its center.
        # self.center_obj.move(dx, dy) # Removed duplicate call
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
        self.rotation = 0  # Rotation angle in degrees
        
        # Store original dimensions (before any rotation)
        p0_pos = p1_obj.pos()
        p2_pos = p3_obj.pos()
        self.original_half_width = abs(p2_pos.x() - p0_pos.x()) / 2
        self.original_half_height = abs(p2_pos.y() - p0_pos.y()) / 2
        
        # Store original center
        self.original_center = QPointF(
            (p0_pos.x() + p2_pos.x()) / 2,
            (p0_pos.y() + p2_pos.y()) / 2
        )
    
    def draw(self, painter, overlay_rect=None):
        pen_width = 1 if self.filled else self.width
        painter.setPen(QPen(self.color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        if self.filled:
            fill_color = QColor(self.color)
            fill_color.setAlpha(100) # Ajustar transparencia: 0 (invisible) a 255 (opaco)
            painter.setBrush(fill_color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Get current point positions (already rotated by rotate() method)
        pts = [p.pos() for p in self.points]
        
        # Draw Polygon - points are already in their final rotated positions
        painter.drawPolygon(pts)

    def contains(self, point, tolerance=None):
        # Check distance to each of the 4 segments
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
    
    def get_center(self):
        """Calculate and return the center point of the rectangle"""
        pts = [p.pos() for p in self.points]
        cx = sum(p.x() for p in pts) / 4
        cy = sum(p.y() for p in pts) / 4
        return QPointF(cx, cy)
    
    def get_rotation_handle_pos(self):
        """Get position for the rotation handle (above top-right corner)"""
        center = self.get_center()
        # Get top-right point (assuming p2 is top-right)
        top_right = self.points[1].pos()
        
        # Position handle 30 pixels above and to the right
        handle_x = top_right.x() + 10
        handle_y = top_right.y() - 30
        
        return QPoint(int(handle_x), int(handle_y))
    
    def rotate(self, angle_degrees):
        """Rotate the rectangle by the given angle around its center"""
        import math
        
        # Store the absolute rotation
        self.rotation = angle_degrees
        
        # Use the current center (which may have moved)
        center = self.get_center()
        cx, cy = center.x(), center.y()
        
        # Use the stored original dimensions (not recalculated)
        half_width = self.original_half_width
        half_height = self.original_half_height
        
        # Define the 4 corners in local coordinates (relative to center)
        # Assuming: p0=top-left, p1=top-right, p2=bottom-right, p3=bottom-left
        local_corners = [
            (-half_width, -half_height),  # Top-left
            (half_width, -half_height),   # Top-right
            (half_width, half_height),    # Bottom-right
            (-half_width, half_height)    # Bottom-left
        ]
        
        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Rotate each corner and update point positions
        for i, (lx, ly) in enumerate(local_corners):
            # Apply rotation matrix
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            
            # Convert back to global coordinates
            new_x = cx + rotated_x
            new_y = cy + rotated_y
            
            # Update the point's position
            self.points[i].x = int(new_x)
            self.points[i].y = int(new_y)

class FreehandObject(DrawingObject):
    def __init__(self, color=Qt.GlobalColor.black, width=3):
        self.path = QPainterPath()
        self.color = color
        self.width = width

    def __deepcopy__(self, memo):
        # QPainterPath is not pickleable, so we manually copy it
        new_obj = FreehandObject(self.color, self.width)
        new_obj.path = QPainterPath(self.path)
        memo[id(self)] = new_obj
        return new_obj

    def draw(self, painter, overlay_rect=None):

        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path)

    def contains(self, point, tolerance=None):
        # Use QPainterPathStroker to create a "fat" path for hit testing
        stroker = QPainterPathStroker()
        hit_width = self.width + (tolerance * 2 if tolerance is not None else 10)
        stroker.setWidth(hit_width)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        
        hit_path = stroker.createStroke(self.path)
        return hit_path.contains(QPointF(point))

    def move(self, dx, dy):
        # Translate the entire path
        from PyQt6.QtGui import QTransform
        transform = QTransform().translate(dx, dy)
        self.path = transform.map(self.path)


class TextObject(DrawingObject):
    def __init__(self, rect_corner1, rect_corner2, text, font_size=16, color=Qt.GlobalColor.black):
        """
        Create a text object within a rectangular boundary.
        
        Args:
            rect_corner1: QPoint for one corner of the rectangle
            rect_corner2: QPoint for the opposite corner
            text: String content to display
            font_size: Size of the font (default 16)
            color: Color of the text (default black)
        """
        # Store corners as mutable QPoint objects for resizing
        self.rect_corner1 = QPoint(rect_corner1.x(), rect_corner1.y())
        self.rect_corner2 = QPoint(rect_corner2.x(), rect_corner2.y())
        self.text = text
        self.font_size = font_size
        self.color = color
    
    def get_rect(self):
        """Get the normalized QRect for the text boundary"""
        return QRect(self.rect_corner1, self.rect_corner2).normalized()
    
    def draw(self, painter, overlay_rect=None):
        rect = self.get_rect()
        
        # Draw rectangle border - ALWAYS WHITE
        painter.setPen(QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        
        # Draw text inside the rectangle with the configured color
        painter.setPen(QPen(self.color, 1, Qt.PenStyle.SolidLine))
        font = QFont()
        font.setPixelSize(self.font_size)
        painter.setFont(font)
        
        # Add some padding to the text
        text_rect = rect.adjusted(5, 5, -5, -5)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, self.text)
    
    def contains(self, point, tolerance=None):
        """Check if point is inside the text rectangle"""
        rect = self.get_rect()
        threshold = int(tolerance) if tolerance is not None else 10
        
        # Expand rect by threshold for easier selection
        expanded_rect = rect.adjusted(-threshold, -threshold, threshold, threshold)
        return expanded_rect.contains(point)
    
    def contains_corner(self, point, tolerance=10):
        """Check if point is near a corner for resizing"""
        threshold = int(tolerance)
        
        # Check all four corners
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
                return i  # Return corner index
        
        return None
    
    def move(self, dx, dy):
        """Move the text object by the given offset"""
        self.rect_corner1 = QPoint(self.rect_corner1.x() + dx, self.rect_corner1.y() + dy)
        self.rect_corner2 = QPoint(self.rect_corner2.x() + dx, self.rect_corner2.y() + dy)


