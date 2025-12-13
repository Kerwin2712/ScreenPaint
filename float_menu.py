from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QEvent
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QBoxLayout, QMenu
from PyQt6.QtGui import QAction, QCursor


class FloatingMenu(QWidget):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(50, 50) # Fixed size now since no handle
        
        # Position variables for dragging
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Main Menu Button
        self.button = QPushButton("☰")
        self.button.setFixedSize(50, 50)
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 25px;
                font-size: 24px;
                border: 2px solid #555555;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        self.button.clicked.connect(self.clicked.emit)
        # Install event filter to handle dragging
        self.button.installEventFilter(self)
        layout.addWidget(self.button)

    def eventFilter(self, source, event):
        if source == self.button:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.dragging = False # Reset
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.window_start_pos = self.frameGeometry().topLeft()
                    # Do NOT absorb event, let button receive Press for visual feedback
            
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    current_pos = event.globalPosition().toPoint()
                    if not self.dragging:
                        if (current_pos - self.drag_start_pos).manhattanLength() > 5:
                            self.dragging = True
                    
                    if self.dragging:
                        delta = current_pos - self.drag_start_pos
                        self.move(self.window_start_pos + delta)
                        return True # Consume event so button ignores it (no click on release)
            
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.dragging:
                    self.dragging = False
                    return True # Consume release, prevent Click
                    
        return super().eventFilter(source, event)

class Toolbar(QWidget):
    toggle_overlay = pyqtSignal()
    hide_toolbar = pyqtSignal()
    close_app = pyqtSignal()
    # New signals for tools
    tool_pen = pyqtSignal()
    tool_eraser = pyqtSignal()
    tool_eraser = pyqtSignal()
    tool_clear = pyqtSignal()
    # Signals for Line Tools
    tool_line_segment = pyqtSignal()
    tool_line_ray = pyqtSignal()
    tool_line_infinite = pyqtSignal()
    tool_line_horizontal = pyqtSignal()
    tool_line_vertical = pyqtSignal()
    tool_line_parallel = pyqtSignal()
    tool_line_perpendicular = pyqtSignal()
    # Signal for Circle Tools
    tool_circle_radius = pyqtSignal()
    tool_circle_center_point = pyqtSignal() # Centro a Punto
    tool_circle_compass = pyqtSignal()      # Compas
    # Signals for Object Tools
    tool_point = pyqtSignal()
    tool_hand = pyqtSignal()
    tool_paint = pyqtSignal() # Paint Bucket
    tool_rectangle = pyqtSignal()
    tool_rectangle = pyqtSignal()
    tool_rectangle_filled = pyqtSignal()
    # Signals for Camera
    tool_capture_full = pyqtSignal()
    tool_capture_crop = pyqtSignal()
    tool_record_full = pyqtSignal()
    tool_record_crop = pyqtSignal()

    # Signals for Undo/Redo
    tool_undo = pyqtSignal()
    tool_redo = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dragging state
        self.dragging = False
        self.offset = QPoint()
        
        layout = QHBoxLayout()
        # Add some margin so there's space to grab if needed, or tight pack with handle
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # Style for buttons
        btn_style = """
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """

        # Drag Handle (Grip)
        self.label_grip = QLabel("✥")
        self.label_grip.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 5px;
                background-color: #222222;
                border-radius: 5px;
            }
            QLabel:hover {
                background-color: #333333;
                color: white;
            }
        """)
        self.label_grip.setToolTip("Arrastrar para mover")
        layout.addWidget(self.label_grip)

        # Hide Toolbar Button (Moved here)
        self.btn_hide = QPushButton("-")
        self.btn_hide.setToolTip("Ocultar Barra")
        self.btn_hide.setStyleSheet(btn_style)
        self.btn_hide.clicked.connect(self.hide_toolbar.emit)
        layout.addWidget(self.btn_hide)

        # Toggle Overlay Button
        self.btn_toggle = QPushButton("👁️")
        self.btn_toggle.setToolTip("Mostrar/Ocultar Overlay")
        self.btn_toggle.setStyleSheet(btn_style)
        self.btn_toggle.clicked.connect(self.toggle_overlay.emit)
        layout.addWidget(self.btn_toggle)

        # Pen Button
        self.btn_pen = QPushButton("✏️")
        self.btn_pen.setToolTip("Lápiz")
        self.btn_pen.setStyleSheet(btn_style)
        self.btn_pen.clicked.connect(self.tool_pen.emit)
        layout.addWidget(self.btn_pen)

        # Line Tool Button with Menu
        self.btn_line = QPushButton("📏")
        self.btn_line.setToolTip("Herramientas de Línea")
        self.btn_line.setStyleSheet(btn_style)
        
        # Create Menu
        self.line_menu = QMenu(self)
        self.line_menu.setStyleSheet("""
            QMenu {
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 10px;
            }
            QMenu::item:selected {
                background-color: #444444;
            }
        """)
        
        # Add Actions
        action_segment = QAction("Segmento", self)
        action_segment.triggered.connect(self.tool_line_segment.emit)
        self.line_menu.addAction(action_segment)
        
        action_ray = QAction("Semirecta", self)
        action_ray.triggered.connect(self.tool_line_ray.emit)
        self.line_menu.addAction(action_ray)
        
        action_infinite = QAction("Recta", self)
        action_infinite.triggered.connect(self.tool_line_infinite.emit)
        self.line_menu.addAction(action_infinite)
        
        action_horizontal = QAction("Recta Horizontal", self)
        action_horizontal.triggered.connect(self.tool_line_horizontal.emit)
        self.line_menu.addAction(action_horizontal)
        
        action_vertical = QAction("Recta Vertical", self)
        action_vertical.triggered.connect(self.tool_line_vertical.emit)
        self.line_menu.addAction(action_vertical)
        
        # Tools requiring a reference line
        self.line_menu.addSeparator()
        
        action_parallel = QAction("Paralela", self)
        action_parallel.triggered.connect(self.tool_line_parallel.emit)
        self.line_menu.addAction(action_parallel)
        
        action_perpendicular = QAction("Perpendicular", self)
        action_perpendicular.triggered.connect(self.tool_line_perpendicular.emit)
        self.line_menu.addAction(action_perpendicular)

        # Set Menu via built-in setMenu logic (though we trigger it on hover)
        self.btn_line.setMenu(self.line_menu)
        
        # Circle Tool Button with Menu
        self.btn_circle = QPushButton("⭕")
        self.btn_circle.setToolTip("Herramientas de Círculo")
        self.btn_circle.setStyleSheet(btn_style)
        
        # Create Circle Menu
        self.circle_menu = QMenu(self)
        self.circle_menu.setStyleSheet("""
            QMenu {
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #444444;
            }
        """)
        
        action_radius = QAction("Centro y Radio", self)
        action_radius.triggered.connect(self.tool_circle_radius.emit)
        self.circle_menu.addAction(action_radius)
        
        action_center_point = QAction("Centro a Punto", self)
        action_center_point.triggered.connect(self.tool_circle_center_point.emit)
        self.circle_menu.addAction(action_center_point)
        
        action_compass = QAction("Compás", self)
        action_compass.triggered.connect(self.tool_circle_compass.emit)
        self.circle_menu.addAction(action_compass)
        
        self.btn_circle.setMenu(self.circle_menu)
        self.btn_circle.setMenu(self.circle_menu)
        layout.addWidget(self.btn_circle)

        # Hook up hover for Circle menu too
        self.btn_circle.installEventFilter(self)
        
        # Rectangle Tool Button
        self.btn_rect = QPushButton("▭")
        self.btn_rect.setToolTip("Rectángulo")
        self.btn_rect.setStyleSheet(btn_style)
        
        # Create Rectangle Menu
        self.rect_menu = QMenu(self)
        self.rect_menu.setStyleSheet("""
            QMenu {
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #444444;
            }
        """)
        
        action_rect = QAction("Rectángulo", self)
        action_rect.triggered.connect(self.tool_rectangle.emit)
        self.rect_menu.addAction(action_rect)

        action_rect_filled = QAction("Rectángulo Relleno", self)
        action_rect_filled.triggered.connect(self.tool_rectangle_filled.emit)
        self.rect_menu.addAction(action_rect_filled)
        
        self.btn_rect.setMenu(self.rect_menu)
        layout.addWidget(self.btn_rect)

        # Hook up hover
        self.btn_rect.installEventFilter(self)

        # Camera Button
        self.btn_cam = QPushButton("📷")
        self.btn_cam.setToolTip("Cámara")
        self.btn_cam.setStyleSheet(btn_style)
        
        self.cam_menu = QMenu(self)
        self.cam_menu.setStyleSheet(self.rect_menu.styleSheet()) # Reuse style
        
        act_cap_full = QAction("Capturar Pantalla", self)
        act_cap_full.triggered.connect(self.tool_capture_full.emit)
        self.cam_menu.addAction(act_cap_full)
        
        act_cap_crop = QAction("Capturar Recorte", self)
        act_cap_crop.triggered.connect(self.tool_capture_crop.emit)
        self.cam_menu.addAction(act_cap_crop)
        
        self.cam_menu.addSeparator()
        
        act_rec_full = QAction("Grabar Pantalla", self)
        act_rec_full.triggered.connect(self.tool_record_full.emit)
        self.cam_menu.addAction(act_rec_full)
        
        act_rec_crop = QAction("Grabar Recorte", self)
        act_rec_crop.triggered.connect(self.tool_record_crop.emit)
        self.cam_menu.addAction(act_rec_crop)
        
        self.btn_cam.setMenu(self.cam_menu)
        self.btn_cam.installEventFilter(self)
        
        layout.addWidget(self.btn_cam)


        # Hook up hover for Circle menu too
        self.btn_circle.installEventFilter(self)
        
        # Install Event Filter to handle Hover
        self.btn_line.installEventFilter(self)
        
        layout.addWidget(self.btn_line)

        # Point Button
        self.btn_point = QPushButton("📍") # Or •
        self.btn_point.setToolTip("Punto")
        self.btn_point.setStyleSheet(btn_style)
        self.btn_point.clicked.connect(self.tool_point.emit)
        layout.addWidget(self.btn_point)

        # Move/Hand Button
        self.btn_hand = QPushButton("✋")
        self.btn_hand.setToolTip("Mover Objetos")
        self.btn_hand.setStyleSheet(btn_style)
        self.btn_hand.clicked.connect(self.tool_hand.emit)
        layout.addWidget(self.btn_hand)

        # Paint Bucket Button
        self.btn_paint = QPushButton("🎨")
        self.btn_paint.setToolTip("Cubo de Pintura (Color)")
        self.btn_paint.setStyleSheet(btn_style)
        self.btn_paint.clicked.connect(self.tool_paint.emit)
        layout.addWidget(self.btn_paint)

        # Undo/Redo Buttons (Before Eraser)
        self.btn_undo = QPushButton("↩️")
        self.btn_undo.setToolTip("Deshacer")
        self.btn_undo.setStyleSheet(btn_style)
        self.btn_undo.clicked.connect(self.tool_undo.emit)
        layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↪️")
        self.btn_redo.setToolTip("Rehacer")
        self.btn_redo.setStyleSheet(btn_style)
        self.btn_redo.clicked.connect(self.tool_redo.emit)
        layout.addWidget(self.btn_redo)

        # Eraser Button
        self.btn_eraser = QPushButton("🧹")
        self.btn_eraser.setToolTip("Borrador")
        self.btn_eraser.setStyleSheet(btn_style)
        self.btn_eraser.clicked.connect(self.tool_eraser.emit)
        layout.addWidget(self.btn_eraser)

        # Clear All Button
        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setToolTip("Limpiar Todo")
        self.btn_clear.setStyleSheet(btn_style)
        self.btn_clear.clicked.connect(self.tool_clear.emit)
        layout.addWidget(self.btn_clear)

        # Close App Button
        self.btn_close = QPushButton("❌")
        self.btn_close.setToolTip("Cerrar Programa")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: 1px solid #990000;
                border-radius: 5px;
                padding: 5px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        self.btn_close.clicked.connect(self.close_app.emit)
        layout.addWidget(self.btn_close)

    def update_toggle_icon(self, is_visible):
        if is_visible:
            self.btn_toggle.setText("👁️")
            self.btn_toggle.setToolTip("Ocultar Lienzo")
        else:
            self.btn_toggle.setText("🙈")
            self.btn_toggle.setToolTip("Mostrar Lienzo")

    def set_layout_rtl(self, is_rtl):
        direction = QBoxLayout.Direction.RightToLeft if is_rtl else QBoxLayout.Direction.LeftToRight
        self.layout().setDirection(direction)
        # Force re-layout/update
        self.layout().update()

    def eventFilter(self, source, event):
        if event.type() == event.Type.Enter:
            if source == self.btn_line:
                self.show_menu(self.btn_line, self.line_menu)
                return True
            elif source == self.btn_circle:
                self.show_menu(self.btn_circle, self.circle_menu)
                return True
            elif source == self.btn_rect:
                self.show_menu(self.btn_rect, self.rect_menu)
                return True
            elif source == self.btn_cam:
                self.show_menu(self.btn_cam, self.cam_menu)
                return True
        return super().eventFilter(source, event)

    def show_menu(self, button, menu):
        # Determine if we should show up or down based on screen geometry
        # Get button global position
        global_pos = button.mapToGlobal(QPoint(0, 0))
        screen = self.window().screen() or button.screen()
        screen_geo = screen.geometry()
        
        menu_height = menu.sizeHint().height()
        
        # Default to showing below
        pos = global_pos + QPoint(0, button.height())
        
        # Check if it fits below
        if global_pos.y() + button.height() + menu_height > screen_geo.bottom():
            # Show above
            pos = global_pos - QPoint(0, menu_height)
            
        menu.exec(pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False
