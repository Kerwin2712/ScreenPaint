from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QEvent
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QBoxLayout, QMenu, QToolTip
from PyQt6.QtGui import QAction, QCursor
from preferences_manager import PreferencesManager


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
    tool_circle_filled = pyqtSignal()       # Centro a Punto (Relleno)
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
    tool_undo = pyqtSignal()
    tool_redo = pyqtSignal()
    
    # Audio Signal
    tool_toggle_audio = pyqtSignal(bool)
    
    # Preferences Signal
    preferences_clicked = pyqtSignal()

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
        self.grip_dragging = False
        self.offset = QPoint()
        self.grip_start_pos = QPoint()

        # Menu Timer
        self.active_menu = None
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(200) # 200ms delay before hiding
        self.hide_timer.timeout.connect(self.hide_active_menu)
        
        # Load preferences
        self.prefs_manager = PreferencesManager()
        self.button_order = self.prefs_manager.load_button_order()
        self.tool_visibility = self.prefs_manager.load_tool_visibility()
        
        # Button references (populated by _create_buttons)
        self.buttons = {}
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # Create all buttons in configured order
        self._create_all_buttons()
    
    def _create_all_buttons(self):
        """Create all toolbar buttons dynamically based on preferences"""
        # Reset specific button references to avoid accessing deleted objects
        self.btn_line = None
        self.btn_rect = None
        self.btn_cam = None
        
        layout = self.layout()
        
        # Button style
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
        
        # Menu style for dropdowns
        menu_style = """
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
        """
        
        # Create buttons in the configured order
        for button_id in self.button_order:
            # Skip if not visible
            if not self.tool_visibility.get(button_id, True):
                continue
            
            # Create appropriate button
            if button_id == 'grip':
                self._add_grip_button(layout)
            elif button_id == 'pen':
                self._add_pen_button(layout, btn_style)
            elif button_id == 'line':
                self._add_line_button(layout, btn_style, menu_style)
            elif button_id == 'shapes':
                self._add_shapes_button(layout, btn_style, menu_style)
            elif button_id == 'camera':
                self._add_camera_button(layout, btn_style, menu_style)
            elif button_id == 'hand':
                self._add_hand_button(layout, btn_style)
            elif button_id == 'paint':
                self._add_paint_button(layout, btn_style)
            elif button_id == 'undo':
                self._add_undo_button(layout, btn_style)
            elif button_id == 'redo':
                self._add_redo_button(layout, btn_style)
            elif button_id == 'eraser':
                self._add_eraser_button(layout, btn_style)
            elif button_id == 'clear':
                self._add_clear_button(layout, btn_style)
            elif button_id == 'preferences':
                self._add_preferences_button(layout, btn_style)
            elif button_id == 'close':
                self._add_close_button(layout)
    
    def _add_grip_button(self, layout):
        """Add grip/drag handle"""
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
        self.label_grip.setToolTip("Arrastrar para mover. Clic para ocultar.")
        self.label_grip.installEventFilter(self)
        layout.addWidget(self.label_grip)
        self.buttons['grip'] = self.label_grip
    
    def _add_pen_button(self, layout, btn_style):
        """Add pen button"""
        self.btn_pen = QPushButton("✏️")
        self.btn_pen.setToolTip("Lápiz")
        self.btn_pen.setStyleSheet(btn_style)
        self.btn_pen.clicked.connect(self.tool_pen.emit)
        self.btn_pen.installEventFilter(self)
        layout.addWidget(self.btn_pen)
        self.buttons['pen'] = self.btn_pen
    
    def _add_line_button(self, layout, btn_style, menu_style):
        """Add line tools button with menu"""
        self.btn_line = QPushButton("📏")
        self.btn_line.setToolTip("Herramientas de Línea")
        self.btn_line.setStyleSheet(btn_style)
        
        self.line_menu = QMenu(self)
        self.line_menu.setStyleSheet(menu_style)
        
        action_point = QAction("Punto", self)
        action_point.triggered.connect(self.tool_point.emit)
        self.line_menu.addAction(action_point)
        self.line_menu.addSeparator()
        
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
        
        self.line_menu.addSeparator()
        
        action_parallel = QAction("Paralela", self)
        action_parallel.triggered.connect(self.tool_line_parallel.emit)
        self.line_menu.addAction(action_parallel)
        
        action_perpendicular = QAction("Perpendicular", self)
        action_perpendicular.triggered.connect(self.tool_line_perpendicular.emit)
        self.line_menu.addAction(action_perpendicular)
        
        self.btn_line.setMenu(self.line_menu)
        self.line_menu.installEventFilter(self)
        self.btn_line.installEventFilter(self)
        layout.addWidget(self.btn_line)
        self.buttons['line'] = self.btn_line
    
    def _add_shapes_button(self, layout, btn_style, menu_style):
        """Add shapes button with menu"""
        self.btn_rect = QPushButton("🔳")
        self.btn_rect.setToolTip("Figuras Geométricas")
        self.btn_rect.setStyleSheet(btn_style)
        
        self.rect_menu = QMenu(self)
        self.rect_menu.setStyleSheet(menu_style)
        
        action_rect = QAction("Rectángulo", self)
        action_rect.triggered.connect(self.tool_rectangle.emit)
        self.rect_menu.addAction(action_rect)
        
        action_rect_filled = QAction("Rectángulo Relleno", self)
        action_rect_filled.triggered.connect(self.tool_rectangle_filled.emit)
        self.rect_menu.addAction(action_rect_filled)
        
        self.rect_menu.addSeparator()
        
        action_center_point = QAction("Círculo", self)
        action_center_point.triggered.connect(self.tool_circle_center_point.emit)
        self.rect_menu.addAction(action_center_point)
        
        action_circle_filled = QAction("Círculo Relleno", self)
        action_circle_filled.triggered.connect(self.tool_circle_filled.emit)
        self.rect_menu.addAction(action_circle_filled)
        
        self.btn_rect.setMenu(self.rect_menu)
        self.rect_menu.installEventFilter(self)
        self.btn_rect.installEventFilter(self)
        layout.addWidget(self.btn_rect)
        self.buttons['shapes'] = self.btn_rect
    
    def _add_camera_button(self, layout, btn_style, menu_style):
        """Add camera button with menu"""
        self.btn_cam = QPushButton("📷")
        self.btn_cam.setToolTip("Cámara")
        self.btn_cam.setStyleSheet(btn_style)
        
        self.cam_menu = QMenu(self)
        self.cam_menu.setStyleSheet(menu_style)
        
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
        
        self.cam_menu.addSeparator()
        
        self.act_audio = QAction("Grabar Audio", self)
        self.act_audio.setCheckable(True)
        self.act_audio.setChecked(True)
        self.act_audio.toggled.connect(self.tool_toggle_audio.emit)
        self.cam_menu.addAction(self.act_audio)
        
        self.btn_cam.setMenu(self.cam_menu)
        self.cam_menu.installEventFilter(self)
        self.btn_cam.installEventFilter(self)
        layout.addWidget(self.btn_cam)
        self.buttons['camera'] = self.btn_cam
    
    def _add_hand_button(self, layout, btn_style):
        """Add hand/move button"""
        self.btn_hand = QPushButton("✋")
        self.btn_hand.setToolTip("Mover Objetos")
        self.btn_hand.setStyleSheet(btn_style)
        self.btn_hand.clicked.connect(self.tool_hand.emit)
        self.btn_hand.installEventFilter(self)
        layout.addWidget(self.btn_hand)
        self.buttons['hand'] = self.btn_hand
    
    def _add_paint_button(self, layout, btn_style):
        """Add paint bucket button"""
        self.btn_paint = QPushButton("🎨")
        self.btn_paint.setToolTip("Color")
        self.btn_paint.setStyleSheet(btn_style)
        self.btn_paint.clicked.connect(self.tool_paint.emit)
        self.btn_paint.installEventFilter(self)
        layout.addWidget(self.btn_paint)
        self.buttons['paint'] = self.btn_paint
    
    def _add_undo_button(self, layout, btn_style):
        """Add undo button"""
        self.btn_undo = QPushButton("↩️")
        self.btn_undo.setToolTip("Deshacer")
        self.btn_undo.setStyleSheet(btn_style)
        self.btn_undo.clicked.connect(self.tool_undo.emit)
        self.btn_undo.installEventFilter(self)
        layout.addWidget(self.btn_undo)
        self.buttons['undo'] = self.btn_undo
    
    def _add_redo_button(self, layout, btn_style):
        """Add redo button"""
        self.btn_redo = QPushButton("↪️")
        self.btn_redo.setToolTip("Rehacer")
        self.btn_redo.setStyleSheet(btn_style)
        self.btn_redo.clicked.connect(self.tool_redo.emit)
        self.btn_redo.installEventFilter(self)
        layout.addWidget(self.btn_redo)
        self.buttons['redo'] = self.btn_redo
    
    def _add_eraser_button(self, layout, btn_style):
        """Add eraser button"""
        self.btn_eraser = QPushButton("🧹")
        self.btn_eraser.setToolTip("Borrador")
        self.btn_eraser.setStyleSheet(btn_style)
        self.btn_eraser.clicked.connect(self.tool_eraser.emit)
        self.btn_eraser.installEventFilter(self)
        layout.addWidget(self.btn_eraser)
        self.buttons['eraser'] = self.btn_eraser
    
    def _add_clear_button(self, layout, btn_style):
        """Add clear all button"""
        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setToolTip("Limpiar Todo")
        self.btn_clear.setStyleSheet(btn_style)
        self.btn_clear.clicked.connect(self.tool_clear.emit)
        self.btn_clear.installEventFilter(self)
        layout.addWidget(self.btn_clear)
        self.buttons['clear'] = self.btn_clear
    
    def _add_preferences_button(self, layout, btn_style):
        """Add preferences button"""
        self.btn_preferences = QPushButton("⚙️")
        self.btn_preferences.setToolTip("Preferencias")
        self.btn_preferences.setStyleSheet(btn_style)
        self.btn_preferences.clicked.connect(self.preferences_clicked.emit)
        self.btn_preferences.installEventFilter(self)
        layout.addWidget(self.btn_preferences)
        self.buttons['preferences'] = self.btn_preferences
    
    def _add_close_button(self, layout):
        """Add close button"""
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
        self.btn_close.installEventFilter(self)
        layout.addWidget(self.btn_close)
        self.buttons['close'] = self.btn_close
    
    def update_from_preferences(self):
        """Reload preferences and rebuild toolbar"""
        # Reload preferences
        self.button_order = self.prefs_manager.load_button_order()
        self.tool_visibility = self.prefs_manager.load_tool_visibility()
        
        # Clear existing buttons
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.buttons.clear()
        
        # Recreate buttons
        self._create_all_buttons()
        
        # Force layout update
        self.adjustSize()

    def hide_active_menu(self):
        if self.active_menu:
            self.active_menu.hide()
            self.active_menu = None

    def set_layout_rtl(self, is_rtl):
        direction = QBoxLayout.Direction.RightToLeft if is_rtl else QBoxLayout.Direction.LeftToRight
        self.layout().setDirection(direction)
        # Force re-layout/update
        self.layout().update()

    def eventFilter(self, source, event):
        if source == self.label_grip:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.grip_dragging = True
                    self.grip_start_pos = event.globalPosition().toPoint()
                    self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self.grip_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                    self.move(event.globalPosition().toPoint() - self.offset)
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.grip_dragging:
                    # Check if it was a click (minimal movement)
                    if (event.globalPosition().toPoint() - self.grip_start_pos).manhattanLength() < 5:
                        self.hide_toolbar.emit()
                    self.grip_dragging = False
                    return True

        if event.type() == QEvent.Type.MouseMove or event.type() == QEvent.Type.Enter:
            # Global check for hovering over buttons when a menu is open
            # This is needed because QMenu might grab mouse events, preventing Enter events on buttons
            if self.active_menu and self.active_menu.isVisible():
                global_pos = QCursor.pos()
                
                # Check Line Button
                if self.btn_line and self.btn_line.isVisible() and self.btn_line.rect().contains(self.btn_line.mapFromGlobal(global_pos)):
                    if self.active_menu != self.line_menu:
                        self.show_menu(self.btn_line, self.line_menu)
                        return True
                # Check Rect Button
                elif self.btn_rect and self.btn_rect.isVisible() and self.btn_rect.rect().contains(self.btn_rect.mapFromGlobal(global_pos)):
                    if self.active_menu != self.rect_menu:
                        self.show_menu(self.btn_rect, self.rect_menu)
                        return True
                # Check Cam Button
                elif self.btn_cam and self.btn_cam.isVisible() and self.btn_cam.rect().contains(self.btn_cam.mapFromGlobal(global_pos)):
                    if self.active_menu != self.cam_menu:
                        self.show_menu(self.btn_cam, self.cam_menu)
                        return True

        if event.type() == QEvent.Type.Enter:
            self.hide_timer.stop() # Stop hiding if re-entered
            
            if isinstance(source, QPushButton):
                QToolTip.showText(QCursor.pos(), source.toolTip(), source)
            
            if source == self.btn_line:
                self.show_menu(self.btn_line, self.line_menu)
                return True
            elif source == self.btn_rect:
                self.show_menu(self.btn_rect, self.rect_menu)
                return True
            elif source == self.btn_cam:
                self.show_menu(self.btn_cam, self.cam_menu)
                return True
            elif isinstance(source, QMenu):
                # Hovering the menu itself, keep it open
                return False

        elif event.type() == QEvent.Type.Leave:
            # If leaving a button or menu, start timer to hide
            buttons_to_check = []
            if self.btn_line: buttons_to_check.append(self.btn_line)
            if self.btn_rect: buttons_to_check.append(self.btn_rect)
            if self.btn_cam: buttons_to_check.append(self.btn_cam)
            
            if source in buttons_to_check or isinstance(source, QMenu):
                self.hide_timer.start()

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
            

            
        # Use popup instead of exec for non-blocking behavior
        if self.active_menu and self.active_menu != menu:
            self.active_menu.hide()
            
        self.active_menu = menu
        self.hide_timer.stop() # Ensure we don't hide immediately
        menu.popup(pos)

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
