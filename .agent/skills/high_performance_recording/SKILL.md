# Skill: Grabación A/V de Alto Rendimiento en Python/Qt

---
name: high_performance_recording
description: Lógica avanzada para grabación de pantalla con sincronización A/V perfecta y arquitectura de hilos desacoplados.
---

## Introducción
Esta skill proporciona los patrones de diseño y scripts necesarios para implementar una grabación de pantalla profesional usando PySide/PyQt, FFmpeg y MSS.

## Estructura de la Skill
- `recording_thread.py`: Patrón productor-consumidor para captura de frames.
- `ffmpeg_pipe.py`: Configuración óptima de pipes para FFmpeg.
- `audio_sync.py`: Lógica de sincronización basada en `perf_counter`.

## Instrucciones de Uso
1. **Hilo de Producción**: Captura frames usando `mss` y colócalos en una `queue.Queue`.
2. **Hilo de Consumo**: Extrae frames de la cola y escríbelos en el `stdin` de un subproceso de FFmpeg.
3. **Mantenimiento de FPS**: Si la cola se llena, descarta frames para priorizar el tiempo real sobre la fluidez excesiva, manteniendo la sincronización con el audio.
4. **Cierre Seguro**: Siempre cierra el pipe de `stdin` y espera a que el proceso de FFmpeg termine suavemente para asegurar que el encabezado del archivo MP4 se escriba correctamente.

## Mejores Prácticas
- Usar `-preset ultrafast` para evitar tirones en el hilo de captura.
- Usar `-pix_fmt yuv420p` para compatibilidad en dispositivos móviles y web.
- Procesar el merge final con `-c:v copy` si el video original ya fue codificado en H.264 durante la captura.
