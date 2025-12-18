import sys
import time
from PyQt6.QtWidgets import QApplication, QBoxLayout
from PyQt6.QtCore import Qt, QObject, QEvent
from globalkeyfilter import GlobalKeyFilter
from float_menu import FloatingMenu, Toolbar
from transparent_overlay import TransparentOverlay
from recording_overlay import ResizableRubberBand
from capture_screen import take_screenshot, ScreenRecorder
from PyQt6.QtWidgets import QFileDialog

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Instantiate windows
    menu = FloatingMenu()
    toolbar = Toolbar()
    toolbar = Toolbar()
    overlay = TransparentOverlay()
    
    # Recording Overlay
    rec_selector = ResizableRubberBand()
    
    # Global Recorder for Full Screen
    full_recorder = None # Placeholder

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

        overlay.showFullScreen() # Show Overlay when menu opens
        # toolbar.update_toggle_icon(False) # Removed since button is gone
        toolbar.show()
        toolbar.raise_()

    def hide_tools():
        # Store current geometry before hiding
        toolbar_geo = toolbar.geometry()
        is_rtl = toolbar.layout().direction() == QBoxLayout.Direction.RightToLeft
        
        toolbar.hide()
        overlay.hide() # Hide Overlay when closing toolbar
        
        if is_rtl:
            # Anchor is at Top-Right. Align Menu Top-Right to Toolbar Top-Right.
            new_x = toolbar_geo.x() + toolbar_geo.width() - menu.width()
            menu.move(new_x, toolbar_geo.y())
        else:
            # Anchor is at Top-Left. Align Menu Top-Left to Toolbar Top-Left.
            menu.move(toolbar_geo.topLeft())
            
        menu.show()
        menu.raise_()

    def close_start():
        app.quit()

    def reset_menu_position():
        menu.move(100, 100)
        menu.show()
        menu.raise_()

    # Install Global Key Filter
    key_filter = GlobalKeyFilter(reset_menu_position)
    app.installEventFilter(key_filter)

    # Connections
    menu.clicked.connect(show_tools)

    toolbar.hide_toolbar.connect(hide_tools)
    toolbar.close_app.connect(close_start)
    
    # Tool Connections
    toolbar.tool_pen.connect(overlay.set_tool_pen)
    toolbar.tool_eraser.connect(overlay.set_tool_eraser)
    toolbar.tool_clear.connect(overlay.clear_canvas)
    
    # Undo/Redo
    toolbar.tool_undo.connect(overlay.undo)
    toolbar.tool_redo.connect(overlay.redo)
    
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
    toolbar.tool_point.connect(overlay.set_tool_point)
    toolbar.tool_hand.connect(overlay.set_tool_hand)
    toolbar.tool_rectangle.connect(overlay.set_tool_rectangle)
    toolbar.tool_rectangle_filled.connect(overlay.set_tool_rectangle_filled)
    toolbar.tool_paint.connect(overlay.set_tool_paint)
    
    # Camera Tools Handlers
    def handle_capture_full():
        # Hide UI
        menu.hide()
        toolbar.hide()
        # overlay.hide() # Keep overlay visible for capture
        rec_selector.hide()
        QApplication.processEvents()
        import time 
        time.sleep(0.2)
        
        fname, _ = QFileDialog.getSaveFileName(None, "Guardar Captura", "", "PNG Files (*.png)")
        if fname:
            take_screenshot(filename=fname)
            
        # Restore
        menu.show()
        # Logic to restore others if they were open? 
        # For simplicity reset to start state or show menu
        
    toolbar.tool_capture_full.connect(handle_capture_full)
    toolbar.tool_capture_crop.connect(overlay.set_tool_capture_crop)
    
    def handle_crop_capture(rect):
        menu.hide()
        toolbar.hide()
        overlay.update() 
        QApplication.processEvents()
        
        import time
        time.sleep(0.1) 
        
        fname, _ = QFileDialog.getSaveFileName(None, "Guardar Recorte", "", "PNG Files (*.png)")
        if fname:
            take_screenshot(rect=rect, filename=fname)
            
        menu.show()
        # Since we triggered this from the toolbar, it was visible. Restore it.
        toolbar.show()
        
        overlay.set_tool_pen()

    overlay.crop_selected.connect(handle_crop_capture)
    
    def handle_record_full():
        # Hide UI
        menu.hide()
        toolbar.hide()
        # overlay.hide() # Keep overlay visible for recording
        QApplication.processEvents()
        
        # Save Dialog
        fname, _ = QFileDialog.getSaveFileName(None, "Grabar Video", "", "Video Files (*.mp4)")
        if fname:
            if not fname.endswith('.mp4'): fname += '.mp4'
            # We need a way to STOP full screen recording. 
            # This implies we need a small floating "Stop" button or hotkey.
            # OR we just show the menu/rec_selector in "minimized" state?
            # User requirement: "Grabar pantalla" (no detailed spec on stop).
            # Simplest: Show the RecSelector but set to Full Screen size and Locked?
            # OR just launch RecSelector covering full screen.
            
            geo = app.primaryScreen().geometry()
            rec_selector.setGeometry(geo.x(), geo.y(), geo.width(), geo.height())
            rec_selector.show()
            # If we reuse RecSelector, it has borders... 
            # Users usually want full screen without border artifacts.
            # But implementing a separate FullScreenRecorder control is extra work.
            # Let's reuse RecSelector for consistency, or implement minimal logic.
            
            pass 
            
    # Better approach for Record Full:
    # Just open the Recording Window but maximized? 
    # Or start recording immediately and provide a notification icon/window to stop.
    # Let's use a specialized small floating "Status" widget for Full Record.
    # For now, to keep it simple and robust:
    # "Grabar Pantalla" -> Opens the Recording Window sized to Full Screen.
    def open_rec_full():
        geo = app.primaryScreen().geometry()
        rec_selector.show()
        rec_selector.setGeometry(geo)
        # Force Full Screen visual cues if needed?
        
    toolbar.tool_record_full.connect(open_rec_full)
    
    def toggle_audio_state(enabled):
        rec_selector.audio_enabled = enabled
        
    toolbar.tool_toggle_audio.connect(toggle_audio_state)
    
    def open_rec_crop():
        rec_selector.show()
        rec_selector.resize(400, 300)
        rec_selector.move(100, 100)
        
    toolbar.tool_record_crop.connect(open_rec_crop)

    # Ensure UI stays on top when interacting with overlay
    def raise_ui():
        toolbar.raise_()
        menu.raise_()
        if rec_selector.isVisible():
            rec_selector.raise_()
    
    overlay.interacted.connect(raise_ui)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
