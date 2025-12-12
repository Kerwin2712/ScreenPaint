import sys
from PyQt6.QtWidgets import QApplication, QBoxLayout
from PyQt6.QtCore import Qt
from float_menu import FloatingMenu, Toolbar
from transparent_overlay import TransparentOverlay

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Instantiate windows
    menu = FloatingMenu()
    toolbar = Toolbar()
    overlay = TransparentOverlay()

    # Initial State
    menu.show()
    # Position menu slightly off-corner by default
    menu.move(100, 100)
    
    toolbar.hide()
    overlay.hide()

    # Logic Functions
    def show_tools():
        menu.hide()
        
        # Smart Positioning Logic
        screen_geo = app.primaryScreen().geometry()
        mid_point = screen_geo.width() / 2
        menu_center = menu.geometry().center().x()
        
        # Ensure toolbar has correct size for interaction
        toolbar.adjustSize() 
        
        if menu_center < mid_point:
            # Left side of screen -> Expand Right -> LTR Layout
            toolbar.set_layout_rtl(False)
            toolbar.adjustSize() # Readjust after layout change
            toolbar.move(menu.pos())
        else:
            # Right side of screen -> Expand Left -> RTL Layout
            toolbar.set_layout_rtl(True)
            toolbar.adjustSize() # Readjust after layout change
            # Position so Top-Right matches Menu Top-Right
            new_x = menu.x() + menu.width() - toolbar.width()
            toolbar.move(new_x, menu.y())

        overlay.showFullScreen()
        toolbar.show()
        toolbar.raise_()

    def hide_tools():
        # Store current geometry before hiding
        toolbar_geo = toolbar.geometry()
        is_rtl = toolbar.layout().direction() == QBoxLayout.Direction.RightToLeft
        
        toolbar.hide()
        
        if is_rtl:
            # Anchor is at Top-Right. Align Menu Top-Right to Toolbar Top-Right.
            new_x = toolbar_geo.x() + toolbar_geo.width() - menu.width()
            menu.move(new_x, toolbar_geo.y())
        else:
            # Anchor is at Top-Left. Align Menu Top-Left to Toolbar Top-Left.
            menu.move(toolbar_geo.topLeft())
            
        menu.show()
        menu.raise_()
        

    def toggle_overlay_visibility():
        if overlay.isVisible():
            overlay.hide()
        else:
            overlay.showFullScreen()
            toolbar.raise_()

    def close_start():
        app.quit()

    # Connections
    menu.clicked.connect(show_tools)
    
    toolbar.toggle_overlay.connect(toggle_overlay_visibility)
    toolbar.hide_toolbar.connect(hide_tools)
    toolbar.close_app.connect(close_start)
    
    # Tool Connections
    toolbar.tool_pen.connect(overlay.set_tool_pen)
    toolbar.tool_eraser.connect(overlay.set_tool_eraser)
    toolbar.tool_clear.connect(overlay.clear_canvas)
    
    # Line Tools
    toolbar.tool_line_segment.connect(overlay.set_tool_line_segment)
    toolbar.tool_line_ray.connect(overlay.set_tool_line_ray)
    toolbar.tool_line_infinite.connect(overlay.set_tool_line_infinite)
    toolbar.tool_line_horizontal.connect(overlay.set_tool_line_horizontal)
    toolbar.tool_line_vertical.connect(overlay.set_tool_line_vertical)
    toolbar.tool_line_parallel.connect(overlay.set_tool_line_parallel)
    toolbar.tool_line_perpendicular.connect(overlay.set_tool_line_perpendicular)

    # Circle Tools
    toolbar.tool_circle_radius.connect(overlay.set_tool_circle_radius)
    toolbar.tool_circle_center_point.connect(overlay.set_tool_circle_center_point)
    toolbar.tool_circle_compass.connect(overlay.set_tool_circle_compass)

    # Object Tools
    toolbar.tool_point.connect(overlay.set_tool_point)
    toolbar.tool_hand.connect(overlay.set_tool_hand)
    toolbar.tool_rectangle.connect(overlay.set_tool_rectangle)

    # Ensure UI stays on top when interacting with overlay
    def raise_ui():
        toolbar.raise_()
        menu.raise_()
    
    overlay.interacted.connect(raise_ui)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
