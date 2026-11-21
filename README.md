# NEOPIXEL PROJECT v1.0 — Sistema Embebido de Iluminación Reactiva e Interfaz 3D

Sistema embebido modular desarrollado en **CircuitPython 10.3+** sobre una placa **Raspberry Pi RP2350 (SuperMini)**. Combina control de iluminación NeoPixel, procesamiento digital de audio en tiempo real mediante micrófono I2S (`audioi2sin` + `ulab`), una interfaz gráfica sin parpadeo sobre pantalla OLED SH1106 con motor de renderizado 3D propio y almacenamiento persistente en memoria no volátil (`NVM`).

---

## Características Principales

* **Arquitectura Modular:** Código separado en módulos independientes por responsabilidad (`persistencia.py`, `efectos_led.py`, `cubo_dvd.py`, `vumetro_i2s.py` y `code.py`).
* **Vúmetro Digital I2S (Estilo WLED Sound Reactive):**
  * Captura de audio a `16 kHz` mediante `audioi2sin.I2SIn`.
  * Eliminación de offset DC y cálculo de energía RMS acelerado por hardware en C (`ulab.numpy`).
  * Puerta de ruido (*Noise Gate*) y Control Automático de Ganancia (*AGC*) con compresión logarítmica ($x^{0.65}$) para responder tanto a sonidos lejanos como a música cercana sin saturación.
  * Indicador *Peak-Hold* con decaimiento suave.
* **Motor Gráfico 3D y UI Zero-Flicker:**
  * Renderizado vectorial en tiempo real de un cubo 3D proyectado en perspectiva sobre `displayio.Bitmap`.
  * *Splash Screen* animado al arranque y salvapantallas estilo DVD tras 5 segundos de inactividad, con inversión de giro y cambio de color vibrante al colisionar con los bordes.
  * Navegación lineal con topes (no circular) mediante encoder rotativo y detección de pulsación corta vs. pulsación larga (`0.75 s`).
* **Persistencia en Memoria No Volátil (`NVM`):**
  * Guarda automáticamente los niveles RGB, el modo de efecto activo, la velocidad del cubo y la calibración del vúmetro directamente en `microcontroller.nvm` (10 bytes empaquetados con firma de validación), evitando bloqueos por sistema de archivos USB de solo lectura y sobreviviendo a cortes de energía.
* **Gestión Segura de Hardware (*Clean Exit*):**
  * Liberación explícita (`deinit()`) de NeoPixels, bus I2S, bus I2C, encoder y pantalla al interrumpir la ejecución (`Ctrl+C`), evitando errores de periféricos ocupados durante depuración en REPL.

---

## Arquitectura del Proyecto

```text
CIRCUITPY/
├── code.py                 # Orquestador principal, máquina de estados de UI y bucle de control
├── persistencia.py         # Lectura y escritura estructurada (struct) en microcontroller.nvm
├── efectos_led.py          # Controlador NeoPixel: RGB manual, Rainbow Wheel y colores vibrantes
├── cubo_dvd.py             # Proyección 3D, trazado Bresenham, Splash Screen y física de rebote DVD
├── vumetro_i2s.py          # Adquisición I2S, cálculo RMS con ulab, puerta de ruido, AGC y peak-hold
└── lib/                    # Librerías externas del CircuitPython Library Bundle (10.x)
    ├── neopixel.mpy
    ├── adafruit_displayio_sh1106.mpy
    ├── adafruit_display_text/
    ├── adafruit_display_shapes/
    └── adafruit_progressbar/