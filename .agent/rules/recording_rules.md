# Reglas del Proyecto ScreenPaint

## Grabación de Pantalla (Crítico)
Para mantener la estabilidad y el rendimiento de la grabación, se deben seguir estas reglas estrictas en el desarrollo:

1. **Arquitectura de Hilos**: Nunca realizar captura de pantalla y codificación de video en el mismo hilo. Usar siempre el patrón productor-consumidor con una cola (`queue.Queue`).
2. **Motor de Captura**: Usar exclusivamente `mss` para capturas en tiempo real en Windows. Evitar `Qt.grabWindow` o `cv2.VideoCapture` de pantalla por su baja tasa de FPS.
3. **Integración con FFmpeg**:
   - Alimentar el proceso vía `stdin` (pipe) para evitar latencia de disco.
   - Usar el preset `ultrafast` para codificación en tiempo real.
   - Especificar `-pix_fmt yuv420p` para garantizar compatibilidad universal del video.
4. **Seguridad de la Interfaz (UI)**:
   - Nunca llamar a `.wait()` en el hilo principal desde el grabador; la detención debe ser asíncrona.
   - Proteger los diálogos de progreso con referencias locales y bloques `try-except` para evitar `AttributeError` por condiciones de carrera entre hilos de Python y C++.
   - No usar `QApplication.processEvents()` en los callbacks de progreso de ffmpeg para evitar reentrada de señales.
5. **Sincronización A/V**: El audio y el video deben unirse en un paso final forzando la duración exacta basada en el tiempo de captura real (`perf_counter`) para evitar desfases al final del archivo.
