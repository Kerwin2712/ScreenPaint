import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from float_menu import FloatingMenu, Toolbar
from transparent_overlay import TransparentOverlay

def main():
    app = QApplication(sys.argv)

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
        # Position toolbar near where the menu was
        toolbar.move(menu.pos())
        overlay.showFullScreen()
        toolbar.show()
        toolbar.raise_()

    def hide_tools():
        toolbar.hide()
        # Position menu where the toolbar was
        menu.move(toolbar.pos())
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

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
