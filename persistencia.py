import struct
import microcontroller

# Firma de 2 bytes ('NP') para validar si ya existen datos guardados
FIRMA_MAGICA = 0x4E50
FORMATO_STRUCT = "<HBBBBBBBB"  # 10 bytes en total
TAMANO_BYTES = struct.calcsize(FORMATO_STRUCT)

MODOS_LISTA = ["MANUAL", "RAINBOW", "RANDOM_DVD", "VUMETRO"]

VALORES_DEFECTO = {
    "r": 60,
    "g": 20,
    "b": 80,
    "modo_led": "MANUAL",
    "vel_cubo": 50,
    "piso_ruido": 35,
    "min_pico_agc": 45,
}


def cargar_configuracion():
    """Lee la configuración desde NVM; si es el primer arranque, devuelve valores por defecto."""
    try:
        datos_crudos = bytes(microcontroller.nvm[0:TAMANO_BYTES])
        firma, r, g, b, idx_modo, vel_cubo, piso_ruido, min_pico_agc, _ = struct.unpack(
            FORMATO_STRUCT, datos_crudos
        )
        if firma != FIRMA_MAGICA:
            return dict(VALORES_DEFECTO)

        modo = MODOS_LISTA[idx_modo] if idx_modo < len(MODOS_LISTA) else "MANUAL"
        return {
            "r": min(100, r),
            "g": min(100, g),
            "b": min(100, b),
            "modo_led": modo,
            "vel_cubo": max(10, min(100, vel_cubo)),
            "piso_ruido": max(5, min(150, piso_ruido)),
            "min_pico_agc": max(5, min(150, min_pico_agc)),
        }
    except Exception:
        return dict(VALORES_DEFECTO)


def guardar_configuracion(cfg):
    """Guarda en NVM solo si algún byte cambió para proteger la vida útil de la flash."""
    idx_modo = MODOS_LISTA.index(cfg["modo_led"]) if cfg["modo_led"] in MODOS_LISTA else 0
    empaquetado = struct.pack(
        FORMATO_STRUCT,
        FIRMA_MAGICA,
        int(cfg["r"]),
        int(cfg["g"]),
        int(cfg["b"]),
        int(idx_modo),
        int(cfg["vel_cubo"]),
        int(cfg["piso_ruido"]),
        int(cfg["min_pico_agc"]),
        0,
    )
    if bytes(microcontroller.nvm[0:TAMANO_BYTES]) != empaquetado:
        microcontroller.nvm[0:TAMANO_BYTES] = empaquetado