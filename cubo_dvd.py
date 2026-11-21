import time
import math
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect

VERTICES = (
    (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
    (-1.0, -1.0,  1.0), (1.0, -1.0,  1.0), (1.0, 1.0,  1.0), (-1.0, 1.0,  1.0),
)
ARISTAS = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


class Cubo3DManager:
    def __init__(self, tam_lienzo=38):
        self.tam_lienzo = tam_lienzo
        self.centro = tam_lienzo // 2

        self.bmp = displayio.Bitmap(tam_lienzo, tam_lienzo, 2)
        paleta = displayio.Palette(2)
        paleta[0] = 0x000000
        paleta[1] = 0xFFFFFF

        # Grupo Salvapantallas DVD
        self.grupo_saver = displayio.Group(x=2)
        self.tile_saver = displayio.TileGrid(self.bmp, pixel_shader=paleta, x=45, y=13)
        self.grupo_saver.append(self.tile_saver)

        # Grupo Splash Screen
        self.grupo_splash = displayio.Group(x=2)
        marco = RoundRect(0, 0, 128, 64, 6, outline=0xFFFFFF, fill=0x000000)
        tile_splash = displayio.TileGrid(self.bmp, pixel_shader=paleta, x=6, y=13)
        lbl_1 = label.Label(terminalio.FONT, text="NEOPIXEL", color=0xFFFFFF, x=56, y=22)
        lbl_2 = label.Label(terminalio.FONT, text="PROJECT", color=0xFFFFFF, x=59, y=34)
        linea = Rect(52, 42, 66, 1, fill=0xFFFFFF)
        lbl_ver = label.Label(terminalio.FONT, text="v1.0", color=0xFFFFFF, x=98, y=54)

        self.grupo_splash.append(marco)
        self.grupo_splash.append(tile_splash)
        self.grupo_splash.append(lbl_1)
        self.grupo_splash.append(lbl_2)
        self.grupo_splash.append(linea)
        self.grupo_splash.append(lbl_ver)

        # Estado de cinemática
        self.angulo_x = 0.0
        self.angulo_y = 0.0
        self.angulo_z = 0.0
        self.dir_rotacion = 1.0

        self.pos_x = 45.0
        self.pos_y = 13.0
        self.dir_x = 1.0
        self.dir_y = 1.0
        self.max_x = 128 - tam_lienzo
        self.max_y = 64 - tam_lienzo

    def _trazar_linea(self, x0, y0, x1, y1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < self.tam_lienzo and 0 <= y0 < self.tam_lienzo:
                self.bmp[x0, y0] = 1
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _renderizar_cubo(self, paso_rot=1.0):
        self.angulo_x += 0.05 * paso_rot
        self.angulo_y += 0.08 * paso_rot
        self.angulo_z += 0.03 * paso_rot

        self.bmp.fill(0)

        cos_x, sin_x = math.cos(self.angulo_x), math.sin(self.angulo_x)
        cos_y, sin_y = math.cos(self.angulo_y), math.sin(self.angulo_y)
        cos_z, sin_z = math.cos(self.angulo_z), math.sin(self.angulo_z)

        puntos_2d = []
        for vx, vy, vz in VERTICES:
            y1 = vy * cos_x - vz * sin_x
            z1 = vy * sin_x + vz * cos_x
            x2 = vx * cos_y + z1 * sin_y
            z2 = -vx * sin_y + z1 * cos_y
            x3 = x2 * cos_z - y1 * sin_z
            y3 = x2 * sin_z + y1 * cos_z

            factor = 31.0 / (z2 + 3.6)
            px = int(self.centro + x3 * factor)
            py = int(self.centro + y3 * factor)
            puntos_2d.append((px, py))

        for idx_a, idx_b in ARISTAS:
            x0, y0 = puntos_2d[idx_a]
            x1, y1 = puntos_2d[idx_b]
            self._trazar_linea(x0, y0, x1, y1)

    def mostrar_splash(self, display, duracion=3.0):
        display.root_group = self.grupo_splash
        inicio = time.monotonic()
        while time.monotonic() - inicio < duracion:
            self._renderizar_cubo(paso_rot=1.2)
            display.refresh()
            time.sleep(0.01)

    def actualizar_dvd(self, velocidad_pct):
        """Actualiza posición y rotación del cubo; devuelve True si rebotó contra una pared."""
        escala_vel = velocidad_pct / 50.0
        self.pos_x += 1.4 * escala_vel * self.dir_x
        self.pos_y += 0.9 * escala_vel * self.dir_y
        reboto = False

        if self.pos_x <= 0:
            self.pos_x = 0
            self.dir_x = 1.0
            reboto = True
        elif self.pos_x >= self.max_x:
            self.pos_x = self.max_x
            self.dir_x = -1.0
            reboto = True

        if self.pos_y <= 0:
            self.pos_y = 0
            self.dir_y = 1.0
            reboto = True
        elif self.pos_y >= self.max_y:
            self.pos_y = self.max_y
            self.dir_y = -1.0
            reboto = True

        if reboto:
            self.dir_rotacion = -self.dir_rotacion

        self.tile_saver.x = int(self.pos_x)
        self.tile_saver.y = int(self.pos_y)
        self._renderizar_cubo(paso_rot=escala_vel * self.dir_rotacion)
        return reboto