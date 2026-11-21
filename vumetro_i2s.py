import array
import math
import audioi2sin
from ulab import numpy as np


class VumetroI2S:
    def __init__(self, bit_clock, word_select, data, num_leds=16, sample_rate=16000,
                 piso_ruido=35, min_pico_agc=45):
        self.num_leds = num_leds
        self.mic = audioi2sin.I2SIn(
            bit_clock=bit_clock,
            word_select=word_select,
            data=data,
            sample_rate=sample_rate,
        )
        self.num_muestras = 256
        self.muestras = array.array("h", [0] * self.num_muestras)

        self.piso_ruido = piso_ruido
        self.min_pico_agc = min_pico_agc
        self.curva_compresion = 0.65

        self.pico_dinamico = float(self.min_pico_agc)
        self.nivel_suavizado = 0.0
        self.led_pico = 0.0

        self.colores_vu = []
        for i in range(self.num_leds):
            ratio = i / (self.num_leds - 1)
            if ratio < 0.55:
                self.colores_vu.append((0, 255, 0))
            elif ratio < 0.85:
                self.colores_vu.append((255, 180, 0))
            else:
                self.colores_vu.append((255, 0, 0))

    def reiniciar_estado(self):
        self.pico_dinamico = float(self.min_pico_agc)
        self.nivel_suavizado = 0.0
        self.led_pico = 0.0

    def actualizar_leds(self, pixels):
        self.mic.record(self.muestras, self.num_muestras)

        datos = np.array(self.muestras, dtype=np.float)
        datos = datos - np.mean(datos)
        rms = math.sqrt(np.mean(datos * datos))

        energia = max(0.0, rms - self.piso_ruido)

        piso_agc = float(self.min_pico_agc)
        if energia > self.pico_dinamico:
            self.pico_dinamico = energia
        else:
            self.pico_dinamico = max(piso_agc, self.pico_dinamico * 0.985)

        ratio_lineal = min(1.0, energia / self.pico_dinamico)
        nivel_objetivo = ratio_lineal ** self.curva_compresion

        if nivel_objetivo > self.nivel_suavizado:
            self.nivel_suavizado = nivel_objetivo
        else:
            self.nivel_suavizado = self.nivel_suavizado * 0.78 + nivel_objetivo * 0.22

        leds_activos = int(round(self.nivel_suavizado * self.num_leds))

        if leds_activos >= self.led_pico:
            self.led_pico = float(leds_activos)
        else:
            self.led_pico = max(0.0, self.led_pico - 0.25)

        for i in range(self.num_leds):
            pixels[i] = self.colores_vu[i] if i < leds_activos else (0, 0, 0)

        idx_pico = int(self.led_pico) - 1
        if 0 <= idx_pico < self.num_leds:
            pixels[idx_pico] = (180, 220, 255)

        pixels.show()

    def deinit(self):
        self.mic.deinit()