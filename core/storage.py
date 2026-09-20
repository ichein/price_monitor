# core/storage.py
# Lee y guarda watchlist/historial; detecta ofertas y cambios de precio.

import math
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Permite ejecutar desde la raíz del proyecto.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.store_base import resultado_precio, EstadoProducto
from core.extras.recode import RAIZ_PROYECTO, _cargar_json, _guardar_json

# Rutas absolutas desde la raíz. Única fuente de verdad — recode.py no las conoce.
WATCHLIST_PATH = RAIZ_PROYECTO / "data" / "watchlist.json"
HISTORY_PATH = RAIZ_PROYECTO / "data" / "price_history.json"

# Plantillas guardadas en el JSON. Única fuente de verdad del schema.
CLAVE_PLANTILLA_WATCHLIST = "producto_formato"
CLAVE_PLANTILLA_HISTORIAL = "producto_historial_formato"

PLANTILLA_WATCHLIST = {
    "tienda": "no one",
    "nombre_producto": "no one",
    "id_producto": "0",
    "id_producto_interno": "0",
    "umbral_aviso": None,
    "peso": 0,
    "activado": False,
    "favorito": False,
}

PLANTILLA_HISTORIAL = {
    "tienda": "no one",
    "nombre_producto": "no one",
    "id_producto": "0",
    "id_producto_interno": "0",
    "historial": [
        {
            "fecha": "D/M/Y",
            "hora": "24h format",
            "fecha_hora": "ISO 8601",
            "estado": "disponible | agotado | sin_precio_region | no_encontrado",
            "oferta": False,
            "precio": "0",
            "descuento": "0",
            "moneda": "MXN",
        }
    ],
    "precio_historico": {
        "moneda": "MXN",
        "historico_bajo": {
            "precio": "0",
            "fecha_hora": "ISO 8601",
        },
        "historico_alto": {
            "precio": "0",
            "fecha_hora": "ISO 8601",
        },
    },
}

# --- helpers propios de este dominio ---

def _clave(tienda: str, id_interno: str) -> str:
    """Clave compuesta."""
    return f"{tienda}:{id_interno}"


def _normalizar_texto(texto) -> str:
    """Normaliza texto."""
    return " ".join(str(texto).split()).casefold()


def _normalizar_umbral(umbral) -> Optional[float]:
    """Normaliza umbral a float; acepta texto o número."""
    if umbral is None or isinstance(umbral, bool):
        if isinstance(umbral, bool):
            raise ValueError("el umbral debe ser un número")
        return None
    if isinstance(umbral, (int, float)):
        valor = float(umbral)
    else:
        texto = str(umbral).strip().replace("$", "").replace(",", "").replace(" ", "")
        if not texto:
            return None
        valor = float(texto)
    if not math.isfinite(valor) or valor < 0:
        raise ValueError("el umbral debe ser un número finito y no negativo")
    return valor


def _leer_umbral(producto: dict) -> Optional[float]:
    """Lee umbral y ignora valores inválidos."""
    try:
        return _normalizar_umbral(producto.get("umbral_aviso"))
    except ValueError:
        print(f"[storage] umbral_aviso inválido ({producto.get('umbral_aviso')!r}) en "
              f"'{producto.get('nombre_producto')}': se ignora.")
        return None


# --- watchlist ---
def cargar_watchlist() -> dict:
    datos = _cargar_json(WATCHLIST_PATH)
    datos.pop(CLAVE_PLANTILLA_WATCHLIST, None)  # es solo plantilla de referencia
    return datos


def guardar_watchlist(productos: dict) -> None:
    _guardar_json(WATCHLIST_PATH, {CLAVE_PLANTILLA_WATCHLIST: PLANTILLA_WATCHLIST, **productos})


def _fusionar_entradas(existente: dict, nueva: dict) -> bool:
    """Fusiona entradas duplicadas."""
    cambio = False
    if existente.get("umbral_aviso") is None and nueva.get("umbral_aviso") is not None:
        existente["umbral_aviso"] = nueva["umbral_aviso"]
        cambio = True
    if not existente.get("peso") and nueva.get("peso"):
        existente["peso"] = nueva["peso"]
        cambio = True
    return cambio


def agregar_producto(tienda: str, nombre_producto: str, id_producto: str,
                      peso: int = 0, umbral_aviso: Optional[float] = None) -> str:
    """Agrega un producto y devuelve su clave."""
    umbral = _normalizar_umbral(umbral_aviso)  # ValueError claro si viene mal
    nuevo = {
        "tienda": tienda,
        "nombre_producto": nombre_producto,
        "id_producto": id_producto,
        "id_producto_interno": "",
        "umbral_aviso": umbral,
        "peso": int(peso),
        "activado": True,
        "favorito": False,
    }
    productos = cargar_watchlist()
    tienda_norm = _normalizar_texto(tienda)
    id_norm = _normalizar_texto(id_producto)
    for clave_existente, existente in productos.items():
        if _normalizar_texto(existente.get("tienda", "")) != tienda_norm:
            continue
        ids_conocidos = {
            _normalizar_texto(existente.get("id_producto", "")),
            _normalizar_texto(existente.get("id_producto_interno", "")),
        }
        if id_norm in ids_conocidos:
            if _fusionar_entradas(existente, nuevo):
                guardar_watchlist(productos)
            return clave_existente
    clave = _clave(tienda, f"tmp-{uuid.uuid4().hex[:12]}")
    productos[clave] = nuevo
    guardar_watchlist(productos)
    return clave


# --- historial de precios ---
def cargar_historial() -> dict:
    datos = _cargar_json(HISTORY_PATH)
    datos.pop(CLAVE_PLANTILLA_HISTORIAL, None)
    return datos


def guardar_historial(historial: dict) -> None:
    _guardar_json(HISTORY_PATH, {CLAVE_PLANTILLA_HISTORIAL: PLANTILLA_HISTORIAL, **historial})


def _entrada_vacia(resultado: resultado_precio) -> dict:
    return {
        "tienda": resultado.tienda,
        "nombre_producto": resultado.titulo,
        "id_producto": resultado.id_producto,
        "id_producto_interno": resultado.id_producto_interno,
        "historial": [],
        "precio_historico": {
            "moneda": resultado.divisa,
            "historico_bajo": None,
            "historico_alto": None,
        },
    }


def _construir_registro(resultado: resultado_precio) -> dict:
    """Construye el registro del historial."""
    momento = datetime.fromisoformat(resultado.timestamp)
    base = {
        "fecha": momento.strftime("%d/%m/%Y"),
        "hora": momento.strftime("%H:%M:%S"),
        "fecha_hora": resultado.timestamp,
        "estado": resultado.estado.value,
    }
    if resultado.estado == EstadoProducto.DISPONIBLE:
        base.update({
            "oferta": resultado.oferta,
            "precio": resultado.precio_actual,
            "descuento": resultado.descuento,
            "moneda": resultado.divisa,
        })
    else:
        base.update({
            "oferta": False,
            "precio": None,
            "descuento": None,
            "moneda": resultado.divisa,
        })
    return base


def _ultimo_precio_de(entrada: dict) -> Optional[float]:
    """Devuelve el último precio válido."""
    for registro in reversed(entrada["historial"]):
        if registro.get("precio") is not None:
            return registro["precio"]
    return None


def obtener_ultimo_precio(tienda: str, id_producto_interno: str) -> Optional[float]:
    """Último precio válido o None."""
    historial = cargar_historial()
    entrada = historial.get(_clave(tienda, id_producto_interno))
    if not entrada:
        return None
    return _ultimo_precio_de(entrada)

def _sincronizar_watchlist(resultado: resultado_precio, clave_watchlist: str, clave_definitiva: str) -> Optional[float]:
    """Sincroniza watchlist y devuelve el umbral."""
    productos = cargar_watchlist()
    producto = productos.get(clave_watchlist)
    if producto is None:
        return None  # el llamador pasó una clave que ya no existe
    cambio = False
    if not producto.get("id_producto_interno"):
        producto["id_producto_interno"] = resultado.id_producto_interno
        cambio = True
    if clave_watchlist != clave_definitiva:
        productos.pop(clave_watchlist)
        existente = productos.get(clave_definitiva)
        if existente is None:
            productos[clave_definitiva] = producto
        else:
            print(f"[storage] '{producto.get('nombre_producto')}' ya estaba en la watchlist " f"como '{clave_definitiva}': se fusionan sin perder la entrada existente.")
            _fusionar_entradas(existente, producto)
            if not existente.get("id_producto_interno"):
                existente["id_producto_interno"] = resultado.id_producto_interno
            producto = existente
        cambio = True
    if cambio:
        guardar_watchlist(productos)
    return _leer_umbral(producto)


if __name__ == "__main__":
    print("storage.py: módulo de persistencia, aún sin prueba de terminal.")

def registrar_resultado(resultado: resultado_precio, clave_watchlist: str) -> dict:
    """Guarda el resultado y devuelve señales."""
    historial = cargar_historial()
    clave_definitiva = _clave(resultado.tienda, resultado.id_producto_interno)
    entrada = historial.get(clave_definitiva)
    if entrada is None:
        entrada = _entrada_vacia(resultado)
        historial[clave_definitiva] = entrada
    # Se calcula ANTES de agregar el registro nuevo (y sobre la copia en memoria, sin releer el archivo).
    precio_anterior = resultado.precio_anterior if resultado.precio_anterior is not None else _ultimo_precio_de(entrada)
    entrada["historial"].append(_construir_registro(resultado))
    disponible = (
        resultado.estado == EstadoProducto.DISPONIBLE
        and resultado.precio_actual is not None
    )
    nuevo_historico_bajo = False
    nuevo_historico_alto = False
    if disponible:
        bajo = entrada["precio_historico"]["historico_bajo"]
        alto = entrada["precio_historico"]["historico_alto"]
        if bajo is None or resultado.precio_actual < bajo["precio"]:
            entrada["precio_historico"]["historico_bajo"] = {
                "precio": resultado.precio_actual, "fecha_hora": resultado.timestamp,
            }
            nuevo_historico_bajo = bajo is not None  # el primer registro no cuenta como "nuevo" mínimo
        if alto is None or resultado.precio_actual > alto["precio"]:
            entrada["precio_historico"]["historico_alto"] = {
                "precio": resultado.precio_actual, "fecha_hora": resultado.timestamp,
            }
            nuevo_historico_alto = alto is not None  # ídem para el máximo
    guardar_historial(historial)
    umbral_aviso = _sincronizar_watchlist(resultado, clave_watchlist, clave_definitiva)
    oferta_nueva = (
        disponible
        and precio_anterior is not None
        and resultado.precio_actual < precio_anterior
    )
    precio_subio = (
        disponible
        and precio_anterior is not None
        and resultado.precio_actual > precio_anterior
    )
    cruzo_umbral = (
        disponible
        and umbral_aviso is not None
        and resultado.precio_actual <= umbral_aviso
        and (precio_anterior is None or precio_anterior > umbral_aviso)
    )

    return {
        "oferta_nueva": oferta_nueva,
        "cruzo_umbral": cruzo_umbral,
        "precio_subio": precio_subio,
        "nuevo_historico_bajo": nuevo_historico_bajo,
        "nuevo_historico_alto": nuevo_historico_alto,
        "precio_anterior": precio_anterior,
        "precio_actual": resultado.precio_actual if disponible else None,
    }