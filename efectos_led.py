import random
import neopixel
import rainbowio


class ControladorLeds:
    def __init__(self, pin, num_leds=16, brillo=0.20):
        self.num_leds = num_leds
        self.pixels = neopixel.NeoPixel(pin, num_leds, brightness=brillo, auto_write=False)
        self.fase_rainbow = 0
        self.ultimo_paso_rainbow = 0.0

    def aplicar_rgb_porcentaje(self, r_pct, g_pct, b_pct):
        r = int(r_pct * 2.55)
        g = int(g_pct * 2.55)
        b = int(b_pct * 2.55)
        self.pixels.fill((r, g, b))
        self.pixels.show()

    def aplicar_color_aleatorio_vibrante(self):
        componentes = [random.randint(150, 255), random.randint(0, 120), 0]
        i1 = random.randint(0, 2)
        i2 = (i1 + random.choice([1, 2])) % 3
        i3 = 3 - i1 - i2
        color = [0, 0, 0]
        color[i1] = componentes[0]
        color[i2] = componentes[1]
        color[i3] = componentes[2]
        self.pixels.fill(tuple(color))
        self.pixels.show()

    def actualizar_rainbow_wheel(self, ahora):
        if ahora - self.ultimo_paso_rainbow >= 0.02:
            self.ultimo_paso_rainbow = ahora
            for i in range(self.num_leds):
                indice_color = (i * 256 // self.num_leds + self.fase_rainbow) & 255
                self.pixels[i] = rainbowio.colorwheel(indice_color)
            self.pixels.show()
            self.fase_rainbow = (self.fase_rainbow + 3) & 255

    def deinit(self):
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
        self.pixels.deinit()