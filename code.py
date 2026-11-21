import time
import board
import busio
import rotaryio
import digitalio
import displayio
import terminalio
import i2cdisplaybus
import adafruit_displayio_sh1106
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_progressbar.horizontalprogressbar import HorizontalProgressBar, HorizontalFillDirection

from persistencia import cargar_configuracion, guardar_configuracion
from efectos_led import ControladorLeds
from cubo_dvd import Cubo3DManager
from vumetro_i2s import VumetroI2S

displayio.release_displays()

# ==============================================================================
# 1. CARGAR AJUSTES PERSISTENTES E INICIALIZAR HARDWARE
# ==============================================================================
cfg = cargar_configuracion()

NUM_LEDS = 16
leds = ControladorLeds(board.GP29, num_leds=NUM_LEDS, brillo=0.20)

i2c = busio.I2C(scl=board.GP1, sda=board.GP0, frequency=400000)
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C)
display = adafruit_displayio_sh1106.SH1106(display_bus, width=130, height=64)
display.auto_refresh = False

encoder = rotaryio.IncrementalEncoder(board.GP2, board.GP3, divisor=4)
boton = digitalio.DigitalInOut(board.GP4)
boton.direction = digitalio.Direction.INPUT
boton.pull = digitalio.Pull.UP

cubo_3d = Cubo3DManager(tam_lienzo=38)

vumetro = VumetroI2S(
    bit_clock=board.GP6,
    word_select=board.GP7,
    data=board.GP8,
    num_leds=NUM_LEDS,
    sample_rate=16000,
    piso_ruido=cfg["piso_ruido"],
    min_pico_agc=cfg["min_pico_agc"],
)


def limpiar_y_liberar():
    """Apaga LEDs, limpia OLED y libera todos los periféricos al salir."""
    print("\nLiberando periféricos y limpiando pantalla...")
    for recurso in (leds, vumetro, encoder, boton):
        try:
            recurso.deinit()
        except Exception:
            pass

    try:
        display.root_group = displayio.Group()
        display.refresh()
    except Exception:
        pass

    try:
        displayio.release_displays()
        i2c.deinit()
    except Exception:
        pass
    print("Periféricos liberados.")


# ==============================================================================
# 2. CONSTRUCCIÓN DE VISTAS DE INTERFAZ OLED
# ==============================================================================
def crear_base_ventana(titulo_texto):
    g = displayio.Group(x=2)
    marco = RoundRect(0, 0, 128, 64, 6, outline=0xFFFFFF, fill=0x000000)
    barra = Rect(4, 4, 120, 12, fill=0xFFFFFF)
    x_centrado = max(6, (128 - len(titulo_texto) * 6) // 2)
    lbl = label.Label(terminalio.FONT, text=titulo_texto, color=0x000000, x=x_centrado, y=10)
    g.append(marco)
    g.append(barra)
    g.append(lbl)
    return g


# VISTA 0: MENÚ PRINCIPAL
grupo_principal = crear_base_ventana("MENU PRINCIPAL")
opciones_principal = ["CONTROL RGB", "EFECTOS"]
cursores_principal = []

for i, texto in enumerate(opciones_principal):
    y_pos = 26 + i * 16
    cur = label.Label(terminalio.FONT, text=">", color=0xFFFFFF, x=14, y=y_pos)
    lbl = label.Label(terminalio.FONT, text=texto, color=0xFFFFFF, x=24, y=y_pos)
    grupo_principal.append(cur)
    grupo_principal.append(lbl)
    cursores_principal.append(cur)

# VISTA 1: SUBMENÚ CONTROL RGB
grupo_rgb = crear_base_ventana("CONTROL RGB")
canales_rgb = [
    {"nombre": "ROJO ", "clave": "r"},
    {"nombre": "VERDE", "clave": "g"},
    {"nombre": "AZUL ", "clave": "b"},
]

filas_rgb_ui = []
for i, canal in enumerate(canales_rgb):
    y_pos = 19 + i * 11
    val_ini = cfg[canal["clave"]]
    cursor = label.Label(terminalio.FONT, text=">", color=0xFFFFFF, x=6, y=y_pos + 3)
    nombre = label.Label(terminalio.FONT, text=canal["nombre"], color=0xFFFFFF, x=14, y=y_pos + 3)
    barra = HorizontalProgressBar(
        (53, y_pos), (52, 7),
        min_value=0, max_value=100, value=val_ini,
        bar_color=0xFFFFFF, outline_color=0xFFFFFF, fill_color=0x000000,
        margin_size=1, direction=HorizontalFillDirection.LEFT_TO_RIGHT,
    )
    pct = label.Label(terminalio.FONT, text=f"{val_ini}", color=0xFFFFFF, x=108, y=y_pos + 3)
    grupo_rgb.append(cursor)
    grupo_rgb.append(nombre)
    grupo_rgb.append(barra)
    grupo_rgb.append(pct)
    filas_rgb_ui.append({"cursor": cursor, "barra": barra, "pct": pct})

cursor_volver_rgb = label.Label(terminalio.FONT, text=">", color=0xFFFFFF, x=6, y=54)
lbl_volver_rgb = label.Label(terminalio.FONT, text="<- VOLVER", color=0xFFFFFF, x=14, y=54)
grupo_rgb.append(cursor_volver_rgb)
grupo_rgb.append(lbl_volver_rgb)

# VISTA 2: SUBMENÚ EFECTOS
grupo_efectos = crear_base_ventana("EFECTOS LED")
opciones_efectos = ["RAINBOW WHEEL", "COLOR DVD (REBOTE)", "VUMETRO I2S", "<- VOLVER"]
cursores_efectos = []

for i, texto in enumerate(opciones_efectos):
    y_pos = 21 + i * 11
    cur = label.Label(terminalio.FONT, text=">", color=0xFFFFFF, x=8, y=y_pos)
    lbl = label.Label(terminalio.FONT, text=texto, color=0xFFFFFF, x=18, y=y_pos)
    grupo_efectos.append(cur)
    grupo_efectos.append(lbl)
    cursores_efectos.append(cur)

# VISTA 2B: VELOCIDAD CUBO DVD
grupo_vel_cubo = crear_base_ventana("VELOCIDAD CUBO")
barra_vel_cubo = HorizontalProgressBar(
    (14, 28), (76, 12),
    min_value=10, max_value=100, value=cfg["vel_cubo"],
    bar_color=0xFFFFFF, outline_color=0xFFFFFF, fill_color=0x000000,
    margin_size=1, direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)
lbl_vel_cubo = label.Label(terminalio.FONT, text=f"{cfg['vel_cubo']}%", color=0xFFFFFF, x=96, y=34)
lbl_ayuda_vel = label.Label(terminalio.FONT, text="Clic para aceptar", color=0xFFFFFF, x=13, y=51)
grupo_vel_cubo.append(barra_vel_cubo)
grupo_vel_cubo.append(lbl_vel_cubo)
grupo_vel_cubo.append(lbl_ayuda_vel)

# VISTA 2C: CALIBRACIÓN VÚMETRO I2S (5..150, PASO 5)
grupo_cal_vu = crear_base_ventana("CALIBRAR VU I2S")
filas_vu_ui = []
params_vu_meta = [
    {"nombre": "SILENCIO", "valor": cfg["piso_ruido"]},
    {"nombre": "LEJANO  ", "valor": cfg["min_pico_agc"]},
]

for i, param in enumerate(params_vu_meta):
    y_pos = 21 + i * 14
    cursor = label.Label(terminalio.FONT, text=">", color=0xFFFFFF, x=5, y=y_pos + 3)
    nombre = label.Label(terminalio.FONT, text=param["nombre"], color=0xFFFFFF, x=13, y=y_pos + 3)
    barra = HorizontalProgressBar(
        (63, y_pos), (42, 8),
        min_value=5, max_value=150, value=param["valor"],
        bar_color=0xFFFFFF, outline_color=0xFFFFFF, fill_color=0x000000,
        margin_size=1, direction=HorizontalFillDirection.LEFT_TO_RIGHT,
    )
    val_lbl = label.Label(terminalio.FONT, text=f"{param['valor']}", color=0xFFFFFF, x=108, y=y_pos + 3)
    grupo_cal_vu.append(cursor)
    grupo_cal_vu.append(nombre)
    grupo_cal_vu.append(barra)
    grupo_cal_vu.append(val_lbl)
    filas_vu_ui.append({"cursor": cursor, "barra": barra, "val": val_lbl})

cursor_volver_vu = label.Label(terminalio.FONT, text=">", color=0xFFFFFF, x=5, y=53)
lbl_volver_vu = label.Label(terminalio.FONT, text="<- VOLVER", color=0xFFFFFF, x=13, y=53)
grupo_cal_vu.append(cursor_volver_vu)
grupo_cal_vu.append(lbl_volver_vu)

# ==============================================================================
# 3. ESTADO DE NAVEGACIÓN Y RENDERIZADO
# ==============================================================================
vista_actual = "PRINCIPAL"
idx_principal = 0
idx_rgb = 0
editando_rgb = False
idx_efectos = 0
idx_cal_vu = 0
editando_cal_vu = False

en_salvapantallas = False
TIEMPO_ESPERA_SAVER = 5.0
TIEMPO_PULSACION_LARGA = 0.75


def aplicar_estado_led_inicial():
    modo = cfg["modo_led"]
    if modo == "MANUAL":
        leds.aplicar_rgb_porcentaje(cfg["r"], cfg["g"], cfg["b"])
    elif modo == "RANDOM_DVD":
        leds.aplicar_color_aleatorio_vibrante()
    elif modo == "VUMETRO":
        vumetro.reiniciar_estado()


def refrescar_ui():
    if vista_actual == "PRINCIPAL":
        for i, cur in enumerate(cursores_principal):
            cur.hidden = (i != idx_principal)
        display.root_group = grupo_principal

    elif vista_actual == "RGB":
        for i, canal in enumerate(canales_rgb):
            ui = filas_rgb_ui[i]
            val = cfg[canal["clave"]]
            ui["cursor"].hidden = (i != idx_rgb)
            ui["cursor"].text = "*" if (i == idx_rgb and editando_rgb) else ">"
            ui["barra"].value = val
            ui["pct"].text = f"{val}"
        cursor_volver_rgb.hidden = (idx_rgb != 3)
        display.root_group = grupo_rgb

    elif vista_actual == "EFECTOS":
        modo = cfg["modo_led"]
        for i, cur in enumerate(cursores_efectos):
            cur.hidden = (i != idx_efectos)
            es_activo = (
                (i == 0 and modo == "RAINBOW")
                or (i == 1 and modo == "RANDOM_DVD")
                or (i == 2 and modo == "VUMETRO")
            )
            cur.text = "*" if es_activo else ">"
        display.root_group = grupo_efectos

    elif vista_actual == "VEL_CUBO":
        barra_vel_cubo.value = cfg["vel_cubo"]
        lbl_vel_cubo.text = f"{cfg['vel_cubo']}%"
        display.root_group = grupo_vel_cubo

    elif vista_actual == "CAL_VU":
        valores = [cfg["piso_ruido"], cfg["min_pico_agc"]]
        for i, val in enumerate(valores):
            ui = filas_vu_ui[i]
            ui["cursor"].hidden = (i != idx_cal_vu)
            ui["cursor"].text = "*" if (i == idx_cal_vu and editando_cal_vu) else ">"
            ui["barra"].value = val
            ui["val"].text = f"{val}"
        cursor_volver_vu.hidden = (idx_cal_vu != 2)
        display.root_group = grupo_cal_vu

    display.refresh()


# ==============================================================================
# 4. BUCLE PRINCIPAL CON NAVEGACIÓN NO CIRCULAR Y CLEAN EXIT
# ==============================================================================
try:
    print("Sistema iniciado. Configuración restaurada desde NVM:", cfg)

    cubo_3d.mostrar_splash(display, duracion=3.0)
    aplicar_estado_led_inicial()
    refrescar_ui()

    ultima_actividad = time.monotonic()
    ultima_pos = encoder.position
    boton_presionado = False
    tiempo_inicio_presion = 0.0
    pulsacion_larga_ejecutada = False

    while True:
        ahora = time.monotonic()
        pos = encoder.position
        estado_btn = boton.value
        hubo_interaccion = False

        # 1. Giro del encoder (menús con tope: no circulares)
        if pos != ultima_pos:
            hubo_interaccion = True
            delta = pos - ultima_pos
            ultima_pos = pos

            if not en_salvapantallas:
                if vista_actual == "PRINCIPAL":
                    idx_principal = max(0, min(len(opciones_principal) - 1, idx_principal + delta))

                elif vista_actual == "RGB":
                    if not editando_rgb:
                        idx_rgb = max(0, min(3, idx_rgb + delta))
                    else:
                        clave = canales_rgb[idx_rgb]["clave"]
                        cfg[clave] = max(0, min(100, cfg[clave] + delta * 5))
                        cfg["modo_led"] = "MANUAL"
                        leds.aplicar_rgb_porcentaje(cfg["r"], cfg["g"], cfg["b"])

                elif vista_actual == "EFECTOS":
                    idx_efectos = max(0, min(len(opciones_efectos) - 1, idx_efectos + delta))

                elif vista_actual == "VEL_CUBO":
                    cfg["vel_cubo"] = max(10, min(100, cfg["vel_cubo"] + delta * 10))

                elif vista_actual == "CAL_VU":
                    if not editando_cal_vu:
                        idx_cal_vu = max(0, min(2, idx_cal_vu + delta))
                    else:
                        if idx_cal_vu == 0:
                            cfg["piso_ruido"] = max(5, min(150, cfg["piso_ruido"] + delta * 5))
                            vumetro.piso_ruido = cfg["piso_ruido"]
                        elif idx_cal_vu == 1:
                            cfg["min_pico_agc"] = max(5, min(150, cfg["min_pico_agc"] + delta * 5))
                            vumetro.min_pico_agc = cfg["min_pico_agc"]
                            vumetro.pico_dinamico = float(cfg["min_pico_agc"])

                refrescar_ui()

        # 2. Pulsación corta vs larga (guardado en NVM al confirmar)
        if not estado_btn:
            hubo_interaccion = True
            if not boton_presionado:
                boton_presionado = True
                tiempo_inicio_presion = ahora
                pulsacion_larga_ejecutada = False
            elif not pulsacion_larga_ejecutada and (ahora - tiempo_inicio_presion >= TIEMPO_PULSACION_LARGA):
                pulsacion_larga_ejecutada = True
                if not en_salvapantallas and vista_actual == "EFECTOS":
                    if idx_efectos == 1:
                        cfg["modo_led"] = "RANDOM_DVD"
                        guardar_configuracion(cfg)
                        vista_actual = "VEL_CUBO"
                        refrescar_ui()
                    elif idx_efectos == 2:
                        cfg["modo_led"] = "VUMETRO"
                        vumetro.reiniciar_estado()
                        guardar_configuracion(cfg)
                        vista_actual = "CAL_VU"
                        idx_cal_vu = 0
                        editando_cal_vu = False
                        refrescar_ui()

        elif boton_presionado:
            hubo_interaccion = True
            boton_presionado = False

            if not pulsacion_larga_ejecutada:
                if en_salvapantallas:
                    pass
                elif vista_actual == "PRINCIPAL":
                    if idx_principal == 0:
                        vista_actual = "RGB"
                        idx_rgb = 0
                        editando_rgb = False
                        cfg["modo_led"] = "MANUAL"
                        leds.aplicar_rgb_porcentaje(cfg["r"], cfg["g"], cfg["b"])
                        guardar_configuracion(cfg)
                    else:
                        vista_actual = "EFECTOS"
                        idx_efectos = 0

                elif vista_actual == "RGB":
                    if idx_rgb == 3:
                        guardar_configuracion(cfg)
                        vista_actual = "PRINCIPAL"
                    else:
                        editando_rgb = not editando_rgb
                        if not editando_rgb:
                            guardar_configuracion(cfg)

                elif vista_actual == "EFECTOS":
                    if idx_efectos == 0:
                        cfg["modo_led"] = "RAINBOW"
                        guardar_configuracion(cfg)
                    elif idx_efectos == 1:
                        cfg["modo_led"] = "RANDOM_DVD"
                        leds.aplicar_color_aleatorio_vibrante()
                        guardar_configuracion(cfg)
                    elif idx_efectos == 2:
                        cfg["modo_led"] = "VUMETRO"
                        vumetro.reiniciar_estado()
                        guardar_configuracion(cfg)
                    elif idx_efectos == 3:
                        vista_actual = "PRINCIPAL"

                elif vista_actual == "VEL_CUBO":
                    guardar_configuracion(cfg)
                    vista_actual = "EFECTOS"

                elif vista_actual == "CAL_VU":
                    if idx_cal_vu == 2:
                        guardar_configuracion(cfg)
                        vista_actual = "EFECTOS"
                    else:
                        editando_cal_vu = not editando_cal_vu
                        if not editando_cal_vu:
                            guardar_configuracion(cfg)

                refrescar_ui()

        # 3. Reposo y salvapantallas DVD
        if hubo_interaccion:
            ultima_actividad = ahora
            if en_salvapantallas:
                en_salvapantallas = False
                refrescar_ui()

        elif not en_salvapantallas and (ahora - ultima_actividad >= TIEMPO_ESPERA_SAVER):
            en_salvapantallas = True
            display.root_group = cubo_3d.grupo_saver

        # 4. Ejecución continua de efectos
        modo = cfg["modo_led"]
        if modo == "RAINBOW":
            leds.actualizar_rainbow_wheel(ahora)
        elif modo == "VUMETRO":
            vumetro.actualizar_leds(leds.pixels)

        if en_salvapantallas:
            reboto = cubo_3d.actualizar_dvd(cfg["vel_cubo"])
            if reboto and modo == "RANDOM_DVD":
                leds.aplicar_color_aleatorio_vibrante()
            display.refresh()
        elif modo != "VUMETRO":
            time.sleep(0.005)

except KeyboardInterrupt:
    print("\nInterrupción detectada por usuario (Ctrl+C).")
finally:
    limpiar_y_liberar()