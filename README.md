# ScreenPaint

ScreenPaint es una herramienta de productividad diseñada para profesionales, educadores y creadores de contenido que permite dibujar directamente sobre la pantalla mediante un lienzo transparente. Ideal para presentaciones, tutoriales, grabaciones de pantalla y demostraciones de software.

## 🚀 Características Principales

- **Dibujo en Tiempo Real**: Lienzo transparente que cubre toda la pantalla.
- **Set Completo de Herramientas**:
  - Lápiz, Borrador y Pincel.
  - Formas Geométricas: Líneas (segmentos, rayos, infinitas, paralelas, perpendiculares), Círculos y Rectángulos.
  - Inserción de Puntos y Texto Personalizable.
- **Gestión de Acciones**: Soporte completo para Deshacer (Undo) y Rehacer (Redo).
- **Captura y Grabación**:
  - Captura de pantalla completa o de una región seleccionada.
  - Grabación de vídeo con soporte opcional para audio.
- **Interfaz Adaptativa**: Menú flotante inteligente que se posiciona automáticamente para no obstruir el flujo de trabajo.
- **Preferencias Personalizables**: Configuración de atajos de teclado, colores y herramientas visibles.

## 🛠️ Tecnologías Utilizadas

- **Python 3.10+**
- **PyQt6**: Para la interfaz gráfica de usuario y el manejo de ventanas transparentes.
- **OpenCV & NumPy**: Para el procesamiento de imágenes y captura de pantalla.
- **MoviePy & PyAudio**: Para la edición y grabación de vídeo con audio.
- **PyInstaller**: Para la generación de ejecutables.

## 📥 Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/Kerwin2712/ScreenPaint.git
cd ScreenPaint
```

### 2. Crear y activar un entorno virtual
```powershell
# En Windows (PowerShell)
python -m venv env
.\env\Scripts\Activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

## 🎮 Cómo Iniciar

Para ejecutar la aplicación, asegúrate de tener activado tu entorno virtual y ejecuta el archivo principal:

```bash
python main.py
```

- Al iniciar, aparecerá un pequeño **menú flotante**.
- Haz clic en él para desplegar la **barra de herramientas** y activar el lienzo transparente.
- Usa la tecla configurada (por defecto `Ctrl+Shift+R` o similar en preferencias) para resetear la posición del menú si es necesario.

## 📄 Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).
