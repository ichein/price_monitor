# core/scheduler.py
# Gestiona horarios, presupuesto diario por tienda, vueltas de balanceo
# de peso y peticiones manuales del usuario.

import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.extras.recode import RAIZ_PROYECTO, _cargar_json, _guardar_json
from core.store_base import EstadoProducto, store_scraper
from core.storage import cargar_watchlist, guardar_watchlist, obtener_ultimo_precio, registrar_resultado

STORE_CONFIG_PATH = RAIZ_PROYECTO / "store_config.json"
STATE_PATH = RAIZ_PROYECTO / "data" / "scheduler_state.json"

# --- umbrales de balanceo, ajustables ---
LECTURAS_PARA_PRECIO_ESTABLE = 3   # N lecturas seguidas sin cambio -> "estable"
CONSULTAS_MANUALES_PARA_SUBIR_PESO = 2  # consultas del usuario en la vuelta -> +1
PESO_MINIMO = 1
PESO_MAXIMO = 10

# --- carga / guardado de configuración y estado ---

def cargar_config_tiendas() -> dict:
    config = _cargar_json(STORE_CONFIG_PATH)
    reset = config.setdefault("reset_diario", {})
    if not any(reset.get(k, False) for k in ("medianoche", "ventana_movil_24h", "al_iniciar_programa")):
        print("[scheduler] reset_diario no tiene ninguna opción activa; se fuerza 'medianoche'.")
        reset["medianoche"] = True
        _guardar_json(STORE_CONFIG_PATH, config)
    return config

def _estado_default() -> dict:
    return {"vuelta_iniciada": None, "global": {"peticiones_usadas_hoy": 0, "ultimo_reset": None},
            "tiendas": {}, "productos": {}}

def cargar_estado() -> dict:
    try:
        estado = _cargar_json(STATE_PATH)
    except FileNotFoundError:
        estado = _estado_default()
    estado.setdefault("global", {"peticiones_usadas_hoy": 0, "ultimo_reset": None})
    estado.setdefault("tiendas", {})
    estado.setdefault("productos", {})
    return estado

def guardar_estado(estado: dict) -> None:
    _guardar_json(STATE_PATH, estado)

def _estado_tienda(estado: dict, tienda: str) -> dict:
    return estado["tiendas"].setdefault(tienda, {
        "peticiones_usadas_hoy": 0, "ultimo_reset": None, "ultima_peticion": None,
    })

def _estado_producto(estado: dict, clave: str) -> dict:
    return estado["productos"].setdefault(clave, {
        "atendido_en_vuelta": False,
        "pendiente_desde": None,
        "ultima_atencion": None,
        "racha_precio_estable": 0,
        "consultas_usuario_en_vuelta": 0,
        "tuvo_pendiente_en_vuelta": False,
    })

# --- reseteo diario de presupuesto ---

def _debe_resetear(seccion_estado: dict, reset_config: dict, ahora: datetime) -> bool:
    ultimo_reset = seccion_estado.get("ultimo_reset")
    if ultimo_reset is None:
        return True
    ultimo = datetime.fromisoformat(ultimo_reset)
    if reset_config.get("medianoche") and ultimo.date() < ahora.date():
        return True
    if reset_config.get("ventana_movil_24h") and (ahora - ultimo) >= timedelta(hours=24):
        return True
    return False

def resetear_presupuesto_si_corresponde(estado: dict, config: dict, ahora: Optional[datetime] = None) -> None:
    """Resetea contadores de peticiones (global y por tienda) según las
    opciones activas en reset_diario. No toca 'atendido_en_vuelta': eso
    solo se resetea al cerrar una vuelta completa, no cada día."""
    ahora = ahora or datetime.now().astimezone()
    reset_config = config.get("reset_diario", {})
    if _debe_resetear(estado["global"], reset_config, ahora):
        estado["global"]["peticiones_usadas_hoy"] = 0
        estado["global"]["ultimo_reset"] = ahora.isoformat(timespec="seconds")
    for tienda in config.get("tiendas", {}):
        seccion = _estado_tienda(estado, tienda)
        if _debe_resetear(seccion, reset_config, ahora):
            seccion["peticiones_usadas_hoy"] = 0
            seccion["ultimo_reset"] = ahora.isoformat(timespec="seconds")

def marcar_reset_al_iniciar(estado: dict, config: dict, ahora: Optional[datetime] = None) -> None:
    """Se llama una sola vez al arrancar el programa, si 'al_iniciar_programa'
    está activo en reset_diario."""
    if not config.get("reset_diario", {}).get("al_iniciar_programa"):
        return
    ahora = ahora or datetime.now().astimezone()
    estado["global"]["peticiones_usadas_hoy"] = 0
    estado["global"]["ultimo_reset"] = ahora.isoformat(timespec="seconds")
    for tienda in config.get("tiendas", {}):
        seccion = _estado_tienda(estado, tienda)
        seccion["peticiones_usadas_hoy"] = 0
        seccion["ultimo_reset"] = ahora.isoformat(timespec="seconds")

# --- presupuesto disponible ---

def presupuesto_disponible(tienda: str, estado: dict, config: dict) -> int:
    tienda_cfg = config["tiendas"].get(tienda)
    if tienda_cfg is None:
        return 0
    seccion = _estado_tienda(estado, tienda)
    restante_tienda = tienda_cfg["peticiones_max_dia"] - seccion["peticiones_usadas_hoy"]
    limite_global = config.get("limite_global", {})
    if limite_global.get("activo", False):
        restante_global = limite_global["peticiones_max_dia"] - estado["global"]["peticiones_usadas_hoy"]
        return max(0, min(restante_tienda, restante_global))
    return max(0, restante_tienda)

# --- construcción de la cola por tienda ---

def _productos_de_tienda(watchlist: dict, tienda: str):
    for clave, producto in watchlist.items():
        if producto.get("tienda") == tienda and producto.get("activado") and producto.get("peso", 0) >= 1:
            yield clave, producto

def construir_cola(tienda: str, watchlist: dict, estado: dict) -> list:
    """Ordena: primero los que quedaron pendientes de días anteriores
    (arrastre), luego por peso descendente, y como último desempate,
    los que llevan más tiempo sin atenderse."""
    candidatos = []
    for clave, producto in _productos_de_tienda(watchlist, tienda):
        est = _estado_producto(estado, clave)
        if est["atendido_en_vuelta"]:
            continue  # ya recibió su petición garantizada en esta vuelta
        candidatos.append((clave, producto, est))
    def _orden(item):
        clave, producto, est = item
        pendiente = 0 if est["pendiente_desde"] else 1  # pendientes primero
        peso = -producto.get("peso", 0)  # mayor peso primero
        ultima = est["ultima_atencion"] or ""  # nunca atendido primero
        return (pendiente, peso, ultima)
    candidatos.sort(key=_orden)
    return candidatos

# --- ejecución de una pasada (procesa lo que el presupuesto permita) ---

def ejecutar_pasada(scrapers: dict) -> dict:
    """scrapers: {"steam": steam_scraper(), "amazon": amazon_scraper(), ...}
    Recorre cada tienda disponible, respeta presupuesto y jitter mínimo,
    guarda resultados vía storage, y actualiza el estado del scheduler.
    Devuelve un resumen simple para que main.py decida qué notificar."""
    config = cargar_config_tiendas()
    estado = cargar_estado()
    resetear_presupuesto_si_corresponde(estado, config)
    watchlist = cargar_watchlist()
    resumen = {"atendidos": [], "ofertas": [], "umbral_cruzado": [], "agotados_o_sin_region": 0}
    for tienda, scraper in scrapers.items():
        tienda_cfg = config["tiendas"].get(tienda)
        if tienda_cfg is None:
            continue
        cola = construir_cola(tienda, watchlist, estado)
        presupuesto = presupuesto_disponible(tienda, estado, config)
        seccion_tienda = _estado_tienda(estado, tienda)
        jitter_minimo = tienda_cfg.get("jitter_minimo_segundos", 0)
        for clave, producto, est_producto in cola[:presupuesto]:
            _respetar_jitter(seccion_tienda, jitter_minimo)
            entrada = producto.get("id_producto_interno") or producto.get("id_producto")
            try:
                resultado = scraper.buscar_precio(entrada)
            except Exception as e:
                print(f"[scheduler] error consultando '{producto.get('nombre_producto')}' en {tienda}: {e}")
                continue
            precio_anterior = obtener_ultimo_precio(tienda, resultado.id_producto_interno)
            señales = registrar_resultado(resultado, clave)
            _actualizar_estado_producto(estado, clave, est_producto, resultado, precio_anterior)
            ahora_iso = datetime.now().astimezone().isoformat(timespec="seconds")
            seccion_tienda["ultima_peticion"] = ahora_iso
            seccion_tienda["peticiones_usadas_hoy"] += 1
            estado["global"]["peticiones_usadas_hoy"] += 1
            resumen["atendidos"].append(clave)
            if señales["oferta_nueva"]:
                resumen["ofertas"].append(clave)
            if señales["cruzo_umbral"]:
                resumen["umbral_cruzado"].append(clave)
            if resultado.estado in (EstadoProducto.AGOTADO, EstadoProducto.SIN_PRECIO_REGION):
                resumen["agotados_o_sin_region"] += 1
    _marcar_pendientes_no_atendidos(estado, watchlist)
    _cerrar_vuelta_si_corresponde(estado, watchlist)
    guardar_estado(estado)
    return resumen

def _respetar_jitter(seccion_tienda: dict, jitter_minimo: int) -> None:
    ultima = seccion_tienda.get("ultima_peticion")
    if ultima is None or jitter_minimo <= 0:
        return
    transcurrido = (datetime.now().astimezone() - datetime.fromisoformat(ultima)).total_seconds()
    faltante = jitter_minimo - transcurrido
    if faltante > 0:
        time.sleep(faltante + random.uniform(0, 5))  # jitter_minimo es el piso, no el valor fijo

def _actualizar_estado_producto(estado: dict, clave: str, est: dict, resultado, precio_anterior, señales: dict) -> None:
    est["atendido_en_vuelta"] = True
    if est["pendiente_desde"] is not None:
        est["tuvo_pendiente_en_vuelta"] = True
    est["pendiente_desde"] = None
    est["ultima_atencion"] = datetime.now().astimezone().isoformat(timespec="seconds")

    if resultado.estado == EstadoProducto.DISPONIBLE and precio_anterior is not None:
        if resultado.precio_actual == precio_anterior:
            est["racha_precio_estable"] += 1
        else:
            est["racha_precio_estable"] = 0

    est["_ultimo_estado"] = resultado.estado.value
    est["_nuevo_extremo_historico"] = señales["nuevo_historico_bajo"] or señales["nuevo_historico_alto"]
    est["_precio_subio"] = señales["precio_subio"]

def _marcar_pendientes_no_atendidos(estado: dict, watchlist: dict) -> None:
    """Al final de la pasada, cualquier producto activo que no alcanzó
    presupuesto queda marcado como pendiente (arrastre)."""
    for clave, producto in watchlist.items():
        if not producto.get("activado") or producto.get("peso", 0) < 1:
            continue
        est = _estado_producto(estado, clave)
        if not est["atendido_en_vuelta"] and est["pendiente_desde"] is None:
            est["pendiente_desde"] = datetime.now().date().isoformat()

# --- cierre de vuelta y balanceo de pesos ---

def _vuelta_completa(estado: dict, watchlist: dict) -> bool:
    activos = [c for c, p in watchlist.items() if p.get("activado") and p.get("peso", 0) >= 1]
    if not activos:
        return False
    return all(_estado_producto(estado, c)["atendido_en_vuelta"] for c in activos)

def _cerrar_vuelta_si_corresponde(estado: dict, watchlist: dict) -> None:
    if not _vuelta_completa(estado, watchlist):
        return
    balancear_pesos(estado, watchlist)
    for clave in watchlist:
        est = _estado_producto(estado, clave)
        est["atendido_en_vuelta"] = False
        est["tuvo_pendiente_en_vuelta"] = False
        est["consultas_usuario_en_vuelta"] = 0
    estado["vuelta_iniciada"] = datetime.now().date().isoformat()
    guardar_watchlist(watchlist)

def balancear_pesos(estado: dict, watchlist: dict) -> None:
    """Aplica las señales acumulables de la vuelta que acaba de cerrar.
    Piso: 1 (el balanceo automático nunca lleva un producto a 0).
    Excepción: NO_ENCONTRADO fuerza el peso a 0 directamente."""
    for clave, producto in watchlist.items():
        if not producto.get("activado") or producto.get("peso", 0) < 1:
            continue
        est = _estado_producto(estado, clave)
        if est.get("_ultimo_estado") == EstadoProducto.NO_ENCONTRADO.value:
            producto["peso"] = 0
            continue
        delta = 0
        # "primero" = se atendió el mismo día en que inició la vuelta (no tuvo que arrastrarse)
        delta += -1 if not est["tuvo_pendiente_en_vuelta"] else +1
        if est["racha_precio_estable"] >= LECTURAS_PARA_PRECIO_ESTABLE:
            delta -= 1
        if est.get("_ultimo_estado") in (EstadoProducto.AGOTADO.value, EstadoProducto.SIN_PRECIO_REGION.value):
            delta -= 1
        if est.get("_nuevo_extremo_historico"):
            delta += 1
        if est.get("_precio_subio"):
            delta -= 1
        if est["consultas_usuario_en_vuelta"] >= CONSULTAS_MANUALES_PARA_SUBIR_PESO:
            delta += 1
        nuevo_peso = producto.get("peso", PESO_MINIMO) + delta
        producto["peso"] = max(PESO_MINIMO, min(PESO_MAXIMO, nuevo_peso))

# --- peticiones manuales del usuario ---

def solicitar_peticion_usuario(tienda: str, clave_watchlist: str, scraper: store_scraper, entrada: str, forzar: bool = False) -> Optional[dict]:
    """Petición fuera de presupuesto (no consume el límite diario), pero
    respeta el límite máximo de la tienda (con advertencia y posibilidad
    de forzar) y el jitter mínimo desde la última petición a esa tienda."""
    config = cargar_config_tiendas()
    estado = cargar_estado()
    tienda_cfg = config["tiendas"].get(tienda)
    if tienda_cfg is None:
        print(f"[scheduler] tienda '{tienda}' no está configurada.")
        return None
    seccion_tienda = _estado_tienda(estado, tienda)
    if seccion_tienda["peticiones_usadas_hoy"] >= tienda_cfg["peticiones_max_dia"] and not forzar:
        print(f"[scheduler] '{tienda}' ya alcanzó su límite diario " f"({tienda_cfg['peticiones_max_dia']}). Puedes forzar la consulta, " "pero hay riesgo de bloqueo por parte de la tienda.")
        return None
    _respetar_jitter(seccion_tienda, tienda_cfg.get("jitter_minimo_segundos", 0) + 5)
    try:
        resultado = scraper.buscar_precio(entrada)
    except Exception as e:
        print(f"[scheduler] error en la consulta manual: {e}")
        return None
    precio_anterior = obtener_ultimo_precio(tienda, resultado.id_producto_interno)
    señales = registrar_resultado(resultado, clave_watchlist)
    est_producto = _estado_producto(estado, clave_watchlist)
    est_producto["consultas_usuario_en_vuelta"] += 1
    seccion_tienda["ultima_peticion"] = datetime.now().astimezone().isoformat(timespec="seconds")
    seccion_tienda["peticiones_usadas_hoy"] += 1  # sí cuenta hacia el límite de la tienda, no hacia el presupuesto de vuelta
    guardar_estado(estado)
    return señales

if __name__ == "__main__":
    print("scheduler.py: módulo de planificación, aún sin prueba de terminal.")