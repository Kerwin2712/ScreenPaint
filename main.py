import sys
import time
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import Qt

# Imports actualizados a nuevas ubicaciones
from ui.globalkeyfilter import GlobalKeyFilter
from ui.float_menu import FloatingMenu, Toolbar
from core.transparent_overlay import TransparentOverlay
from tools.recording_overlay import ScreenRecordingOverlay
from tools.capture_screen import take_screenshot


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Instanciar ventanas
    menu = FloatingMenu()
    toolbar = Toolbar()
    overlay = TransparentOverlay()
    # Overlay de grabación: marco de pantalla completa con panel de control
    recording_overlay = ScreenRecordingOverlay()

    # ===== CAPTURA DE PANTALLA =====

    def handle_full_screenshot():
        overlay.hide()
        toolbar.hide()
        time.sleep(0.3)
        take_screenshot()
        overlay.showFullScreen()
        toolbar.show()
        toolbar.raise_()
        menu.raise_()

    def handle_crop_screenshot(rect):
        overlay.hide()
        toolbar.hide()
        overlay.set_tool_pen()
        time.sleep(0.3)
        take_screenshot(rect=rect)
        overlay.showFullScreen()
        toolbar.show()
        toolbar.raise_()
        menu.raise_()

    # ===== VISIBILIDAD DEL TOOLBAR =====

    def show_toolbar():
        menu.hide()
        toolbar.show()
        toolbar.adjustSize()

        from PyQt6.QtCore import QPoint
        screen_geo = app.primaryScreen().geometry()
        screen_center_x = screen_geo.center().x()

        menu_pos = menu.pos()
        menu_cx = menu_pos.x() + menu.width() // 2
        menu_cy = menu_pos.y() + menu.height() // 2

        # La barra se extiende hacia el centro de pantalla desde donde está el menú
        menu_on_right = menu_cx > screen_center_x
        toolbar.set_layout_rtl(menu_on_right)
        toolbar.adjustSize()

        bar_w = toolbar.width()
        bar_h = toolbar.height()

        if menu_on_right:
            bar_x = menu_pos.x() + menu.width() - bar_w
        else:
            bar_x = menu_pos.x()

        bar_y = menu_cy - bar_h // 2

        bar_x = max(screen_geo.left(), min(bar_x, screen_geo.right() - bar_w))
        bar_y = max(screen_geo.top(), min(bar_y, screen_geo.bottom() - bar_h))

        toolbar.move(bar_x, bar_y)

        # Mostrar overlay y luego subir toolbar encima de él
        overlay.showFullScreen()
        toolbar.raise_()

    def hide_toolbar():
        # Posicionar el menú donde estaba el grip del toolbar
        from PyQt6.QtCore import QPoint
        if hasattr(toolbar, 'label_grip'):
            g = toolbar.label_grip
            grip_global = g.mapToGlobal(QPoint(g.width() // 2, g.height() // 2))
            menu.move(grip_global.x() - menu.width() // 2, grip_global.y() - menu.height() // 2)
        toolbar.hide()
        # Ocultar overlay: no se puede dibujar con la barra cerrada
        overlay.hide()
        menu.show()

    # ===== CONEXIONES: MENU FLOTANTE =====

    menu.clicked.connect(show_toolbar)

    # ===== CONEXIONES: TOOLBAR =====

    toolbar.hide_toolbar.connect(hide_toolbar)
    toolbar.close_app.connect(app.quit)

    toolbar.tool_pen.connect(overlay.set_tool_pen)
    toolbar.tool_eraser.connect(overlay.set_tool_eraser)
    toolbar.tool_clear.connect(overlay.clear_canvas)
    toolbar.tool_line_segment.connect(overlay.set_tool_line_segment)
    toolbar.tool_line_ray.connect(overlay.set_tool_line_ray)
    toolbar.tool_line_infinite.connect(overlay.set_tool_line_infinite)
    toolbar.tool_line_horizontal.connect(overlay.set_tool_line_horizontal)
    toolbar.tool_line_vertical.connect(overlay.set_tool_line_vertical)
    toolbar.tool_line_parallel.connect(overlay.set_tool_line_parallel)
    toolbar.tool_line_perpendicular.connect(overlay.set_tool_line_perpendicular)
    toolbar.tool_circle_radius.connect(overlay.set_tool_circle_radius)
    toolbar.tool_circle_center_point.connect(overlay.set_tool_circle_center_point)
    toolbar.tool_circle_filled.connect(overlay.set_tool_circle_filled)
    toolbar.tool_circle_compass.connect(overlay.set_tool_circle_compass)
    toolbar.tool_point.connect(overlay.set_tool_point)
    toolbar.tool_hand.connect(overlay.set_tool_hand)
    toolbar.tool_paint.connect(overlay.set_tool_paint)
    toolbar.tool_text.connect(overlay.set_tool_text)
    toolbar.tool_rectangle.connect(overlay.set_tool_rectangle)
    toolbar.tool_rectangle_filled.connect(overlay.set_tool_rectangle_filled)
    toolbar.tool_undo.connect(overlay.undo)
    toolbar.tool_redo.connect(overlay.redo)

    toolbar.preferences_clicked.connect(overlay._show_preferences)
    toolbar.preferences_clicked.connect(lambda: toolbar.update_from_preferences())

    def on_toggle_audio(checked):
        recording_overlay.audio_enabled = checked

    toolbar.tool_toggle_audio.connect(on_toggle_audio)

    toolbar.tool_capture_full.connect(handle_full_screenshot)
    toolbar.tool_capture_crop.connect(overlay.set_tool_capture_crop)

    def on_toggle_recording():
        if recording_overlay.isVisible():
            recording_overlay.close_overlay()
        else:
            recording_overlay.show_overlay()

    toolbar.tool_record_full.connect(on_toggle_recording)
    toolbar.tool_record_crop.connect(on_toggle_recording)

    # ===== CONEXIONES: OVERLAY =====

    # Al interactuar, asegurar que toolbar y menú queden siempre encima del overlay
    def on_overlay_interacted():
        toolbar.raise_()
        menu.raise_()

    overlay.interacted.connect(on_overlay_interacted)
    overlay.crop_selected.connect(handle_crop_screenshot)
    overlay.minimize_requested.connect(hide_toolbar)

    # ===== FILTRO GLOBAL DE TECLAS =====

    def on_alt_double_press():
        if toolbar.isVisible():
            hide_toolbar()
        else:
            show_toolbar()

    key_filter = GlobalKeyFilter(on_alt_double_press)
    app.installEventFilter(key_filter)

    # ===== MOSTRAR VENTANAS =====

    # Solo el botón flotante al iniciar; el overlay se muestra al abrir la barra
    screen = app.primaryScreen()
    screen_geo = screen.geometry()
    menu.move(screen_geo.right() - 60, screen_geo.center().y())
    menu.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
