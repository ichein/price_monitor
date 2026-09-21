# core/extras/tema.py
# Paletas de color, generación de QSS y utilidades visuales compartidas
# por las tres ventanas (main, listas, configuracion) y por notifier.py
# (popups). Vive en core/ (no en visuals/) porque notifier.py depende de
# él y no debe depender de la capa visual.

import sys
import weakref
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PyQt6.QtWidgets import QPushButton, QSizePolicy

from core.extras.recode import RAIZ_PROYECTO, RUTA_USER_DATA, _cargar_json, actualizar_seccion

QSS_MAIN_PATH = RAIZ_PROYECTO / "style" / "visual_main.qss"
QSS_POPUP_PATH = RAIZ_PROYECTO / "style" / "popup.qss"

PALETAS = {
    "claro": {
        "BG": "#F7F8F5", "SUPERFICIE": "#FFFFFF", "BORDE": "#E3E6DF",
        "TEXTO": "#1F2A24", "TEXTO_SEC": "#6B7A70",
        "ACENTO": "#5B8A72", "ACENTO_HOVER": "#4A7660", "EXITO": "#7BA88E",
    },
    "oscuro": {
        "BG": "#121614", "SUPERFICIE": "#1C2320", "BORDE": "#2A3330",
        "TEXTO": "#E8EBE9", "TEXTO_SEC": "#8A9691",
        "ACENTO": "#7FB894", "ACENTO_HOVER": "#95C9A8", "EXITO": "#5E9E7A",
    },
}

# Rangos para los deslizadores de configuración visual (min, max).
RANGOS_DESLIZABLES = {
    "tiempo_entrada": (0, 2000),
    "tiempo_salida": (0, 2000),
    "separacion_popups": (0, 150),
    "radio_superior_izquierdo": (0, 40),
    "radio_superior_derecho": (0, 40),
    "radio_inferior_izquierdo": (0, 40),
    "radio_inferior_derecho": (0, 40),
}

_VENTANAS = []  # referencias débiles, para reaplicar el tema en vivo


def registrar_ventana(ventana) -> None:
    """Cada QMainWindow se registra aquí al crearse, para que
    aplicar_modo() pueda re-pintarla sin reiniciarla."""
    _VENTANAS.append(weakref.ref(ventana))


def _ventanas_vivas():
    vivas = []
    for ref in list(_VENTANAS):
        v = ref()
        if v is not None:
            vivas.append(v)
        else:
            _VENTANAS.remove(ref)
    return vivas


def modo_actual() -> str:
    if not RUTA_USER_DATA.exists():
        return "claro"
    try:
        config = _cargar_json(RUTA_USER_DATA)
    except Exception:
        return "claro"
    return config.get("interfaz_config", {}).get("modo", "claro")


def guardar_modo(modo: str) -> None:
    actualizar_seccion(RUTA_USER_DATA, "interfaz_config", {"modo": modo})


def _reemplazar_tokens(texto: str, paleta: dict) -> str:
    for llave, valor in paleta.items():
        texto = texto.replace(f"__{llave}__", valor)
    return texto


def generar_qss_main(modo: str = None) -> str:
    modo = modo or modo_actual()
    paleta = PALETAS.get(modo, PALETAS["claro"])
    try:
        with open(QSS_MAIN_PATH, "r", encoding="utf-8") as archivo:
            plantilla = archivo.read()
    except FileNotFoundError:
        return ""
    return _reemplazar_tokens(plantilla, paleta)


def generar_qss_popup(ajustes: dict, modo: str = None) -> str:
    modo = modo or modo_actual()
    paleta = PALETAS.get(modo, PALETAS["claro"])
    try:
        with open(QSS_POPUP_PATH, "r", encoding="utf-8") as archivo:
            plantilla = archivo.read()
    except FileNotFoundError:
        return ""
    texto = _reemplazar_tokens(plantilla, paleta)
    marcadores_radio = {
        "__RADIO_SUPERIOR_IZQUIERDO__": "radio_superior_izquierdo",
        "__RADIO_SUPERIOR_DERECHO__": "radio_superior_derecho",
        "__RADIO_INFERIOR_IZQUIERDO__": "radio_inferior_izquierdo",
        "__RADIO_INFERIOR_DERECHO__": "radio_inferior_derecho",
    }
    for marcador, llave in marcadores_radio.items():
        texto = texto.replace(marcador, f"{ajustes.get(llave, 0)}px")
    return texto


def aplicar_modo(modo: str) -> None:
    """Guarda el modo elegido y re-pinta todas las ventanas abiertas."""
    guardar_modo(modo)
    qss = generar_qss_main(modo)
    for ventana in _ventanas_vivas():
        ventana.setStyleSheet(qss)


def crear_boton(texto: str, manejador=None) -> QPushButton:
    """Botón que se ajusta a su propio texto en vez de estirarse dentro
    del layout (evita que el texto se vea recortado/ilegible)."""
    boton = QPushButton(texto)
    boton.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    if manejador is not None:
        boton.clicked.connect(manejador)
    return boton