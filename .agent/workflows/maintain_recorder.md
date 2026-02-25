---
description: Cómo realizar el mantenimiento o actualización del motor de grabación sin romper el rendimiento
---

Para modificar o actualizar el motor de grabación, sigue estos pasos rigurosos:

1. **Revisión de Dependencias**:
   - Asegúrate de que `mss`, `pyaudio` e `imageio-ffmpeg` estén instalados en el entorno virtual.
   - Verifica que FFmpeg sea accesible vía `imageio_ffmpeg.get_ffmpeg_exe()`.

2. **Ajuste de FPS**:
   - Si cambias `_TARGET_FPS` en `ScreenRecorder`, asegúrate de actualizarlo tanto en el comando de FFmpeg como en la lógica del temporizador del hilo productor.
   - // turbo
   3. **Verificación de Performance**:
      - Ejecuta la grabación y verifica en consola el mensaje de "FPS real".
      - Si el FPS real cae por debajo del objetivo, revisa si el preset de FFmpeg está en `ultrafast`.

4. **Prueba de Sincronización A/V**:
   - Realiza una grabación de al menos 30 segundos con audio.
   - Verifica que el audio no termine antes que el video en el archivo final.
   - Si hay desfase, ajusta el cálculo de `offset` en el método `_merge_final`.

5. **Validación de UI**:
   - Pulsa "Save" y verifica que el diálogo de progreso aparezca y desaparezca sin lanzar excepciones `AttributeError`.
   - Asegúrate de que no haya caracteres latinos/especiales en los textos enviados a la UI para evitar problemas de encoding en la terminal de Windows.
