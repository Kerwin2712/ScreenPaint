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
        toolbar.show()
        overlay.showFullScreen()

    def hide_tools():
        toolbar.hide()
        # Position menu where the toolbar was
        menu.move(toolbar.pos())
        menu.show()
        # Optional: Hide overlay when minimizing toolbar? 
        # User didn't specify, but usually "hiding toolbar" implies going back to "minimized" state.
        # However, user might want to keep drawing without the toolbar obstructing.
        # Let's keep overlay as is, or maybe hide it? 
        # "otro para ocultar la barra de herramientas". 
        # If I hide the toolbar, how do I bring it back? The menu comes back.
        # If the menu comes back, clicking it shows the toolbar AND overlay.
        # So if I hide toolbar -> show menu.
        

    def toggle_overlay_visibility():
        if overlay.isVisible():
            overlay.hide()
        else:
            overlay.showFullScreen()

    def close_start():
        app.quit()

    # Connections
    menu.clicked.connect(show_tools)
    
    toolbar.toggle_overlay.connect(toggle_overlay_visibility)
    toolbar.hide_toolbar.connect(hide_tools)
    toolbar.close_app.connect(close_start)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
