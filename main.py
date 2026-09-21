# main.py
# Punto de entrada: intérprete de comandos (REPL) que coordina storage,
# scheduler y notifier según lo documentado en commands.json.

import importlib
import json
import shlex
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import storage, scheduler
from core import notifier
from core.store_base import error as StoreError
from core.extras.recode import RAIZ_PROYECTO, RUTA_USER_DATA, y_or_n, modificar_json, limpiar_datos

COMMANDS_PATH = RAIZ_PROYECTO / "commands.json"

# Appid/id de prueba conocido, usado solo por 'probar_conexion'.
IDS_PRUEBA = {"steam": "730"}  # Counter-Strike 2

BOOL_FLAGS = {"confirmar", "forzar", "favoritos", "inactivos"}


# --- carga de comandos y scrapers ---

def cargar_comandos() -> dict:
    try:
        with open(COMMANDS_PATH, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[main] no se pudo cargar commands.json ({e}); 'ayuda' quedará limitada.")
        return {"comandos": {}}


def _cargar_scrapers() -> dict:
    """Intenta importar cada scraper de tienda. Las tiendas no implementadas
    todavía (amazon, mercadolibre) quedan con valor None sin tumbar el
    programa, porque sus archivos aún son placeholders."""
    especificaciones = {
        "steam": ("stores.steam", "steam_scraper"),
        "amazon": ("stores.amazon", "amazon_scraper"),
        "mercadolibre": ("stores.mercadolibre", "mercadolibre_scraper"),
    }
    registros = {}
    for tienda, (modulo, clase) in especificaciones.items():
        try:
            mod = importlib.import_module(modulo)
            registros[tienda] = getattr(mod, clase)()
        except Exception:
            registros[tienda] = None
    return registros


def _leer_config_usuario() -> dict:
    try:
        with open(RUTA_USER_DATA, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# --- parseo de línea de comandos ---

def _parsear(linea: str):
    try:
        partes = shlex.split(linea)
    except ValueError as e:
        print(f"No se pudo interpretar el comando (¿comillas sin cerrar?): {e}")
        return None, [], {}
    if not partes:
        return None, [], {}
    comando = partes[0].lower()
    posicionales, flags = [], {}
    i = 1
    while i < len(partes):
        parte = partes[i]
        if parte.startswith("--"):
            nombre = parte[2:]
            if nombre in BOOL_FLAGS:
                flags[nombre] = True
                i += 1
            elif i + 1 < len(partes):
                flags[nombre] = partes[i + 1]
                i += 2
            else:
                flags[nombre] = True
                i += 1
        else:
            posicionales.append(parte)
            i += 1
    return comando, posicionales, flags


def _resolver_producto(tienda: str, nombre_o_id: str):
    """Búsqueda parcial dentro de la watchlist. None si no hay match único."""
    coincidencias = storage._buscar_productos(tienda, nombre_o_id)
    if not coincidencias:
        print(f"No se encontró ningún producto de '{tienda}' que coincida con '{nombre_o_id}'.")
        return None
    if len(coincidencias) > 1:
        print(f"Hay {len(coincidencias)} productos que coinciden; sé más específico:")
        for _, producto in coincidencias:
            ident = producto.get("id_producto_interno") or producto.get("id_producto")
            print(f"  - {producto.get('nombre_producto')} (id: {ident})")
        return None
    return coincidencias[0]


def _entrada_scraper(producto: dict) -> str:
    return producto.get("id_producto_interno") or producto.get("id_producto")


# --- comandos ---

def cmd_agregar(pos, flags, scrapers, _doc):
    if len(pos) < 2:
        print("Uso: agregar <tienda> <nombre_o_id> [--peso N] [--umbral PRECIO]")
        return
    tienda, entrada = pos[0], pos[1]
    if tienda not in scrapers:
        print(f"'{tienda}' no está configurada en store_config.json.")
        return
    try:
        peso = int(flags.get("peso", 1))
    except ValueError:
        print("--peso debe ser un número entero.")
        return
    try:
        clave = storage.agregar_producto(
            tienda, entrada, entrada, peso=peso, umbral_aviso=flags.get("umbral"),
        )
    except ValueError as e:
        print(f"Error: {e}")
        return
    print(f"Producto agregado. Se resolverá su id real en la próxima consulta (clave interna: {clave}).")


def cmd_quitar(pos, flags, scrapers, _doc):
    if len(pos) < 2:
        print("Uso: quitar <tienda> <nombre_o_id>")
        return
    resultado = _resolver_producto(pos[0], pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    storage.set_activado(clave, False)
    print(f"'{producto.get('nombre_producto')}' desactivado. Su historial se conserva.")


def cmd_borrar(pos, flags, scrapers, _doc):
    if len(pos) < 2:
        print("Uso: borrar <tienda> <nombre_o_id> [--confirmar]")
        return
    resultado = _resolver_producto(pos[0], pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    if not flags.get("confirmar") and not y_or_n(
        f"¿Borrar '{producto.get('nombre_producto')}' y todo su historial? Es irreversible. (Y/N): "
    ):
        print("Cancelado.")
        return
    storage.eliminar_producto(clave)
    print(f"'{producto.get('nombre_producto')}' borrado de la watchlist y del historial.")


def cmd_listar(pos, flags, scrapers, _doc):
    productos = storage.cargar_watchlist()
    filtro_tienda = flags.get("tienda")
    solo_favoritos = bool(flags.get("favoritos"))
    incluir_inactivos = bool(flags.get("inactivos"))

    filas = []
    for producto in productos.values():
        if filtro_tienda and producto.get("tienda") != filtro_tienda:
            continue
        if solo_favoritos and not producto.get("favorito"):
            continue
        if not incluir_inactivos and not producto.get("activado"):
            continue
        filas.append(producto)

    if not filas:
        print("No hay productos que coincidan con ese filtro.")
        return
    for p in filas:
        marca = "★" if p.get("favorito") else " "
        estado = "activo" if p.get("activado") else "inactivo"
        ident = p.get("id_producto_interno") or p.get("id_producto")
        print(f"{marca} [{p.get('tienda')}] {p.get('nombre_producto')} " f"(id: {ident}, peso: {p.get('peso')}, {estado})")


def cmd_consultar(pos, flags, scrapers, _doc):
    if len(pos) < 2:
        print("Uso: consultar <tienda> <nombre_o_id> [--forzar]")
        return
    tienda = pos[0]
    scraper = scrapers.get(tienda)
    if scraper is None:
        print(f"'{tienda}' no tiene un scraper implementado todavía.")
        return
    resultado = _resolver_producto(tienda, pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    señales = scheduler.solicitar_peticion_usuario(
        tienda, clave, scraper, _entrada_scraper(producto), forzar=bool(flags.get("forzar")),
    )
    if señales is None:
        return
    print(f"Precio actual: {señales['precio_actual']} (anterior: {señales['precio_anterior']})")
    if señales["oferta_nueva"]:
        print("¡Bajó de precio!")
    if señales["cruzo_umbral"]:
        print("Cruzó el umbral de aviso configurado.")


def cmd_revisar(pos, flags, scrapers, _doc):
    activos = {t: s for t, s in scrapers.items() if s is not None}
    if not activos:
        print("No hay ninguna tienda con scraper implementado todavía.")
        return
    resumen = scheduler.ejecutar_pasada(activos)
    print(f"Revisión completa: {len(resumen['atendidos'])} productos consultados, " f"{len(resumen['ofertas'])} con oferta nueva, " f"{len(resumen['umbral_cruzado'])} cruzaron su umbral, " f"{resumen['agotados_o_sin_region']} agotados o sin precio en su región.")


def cmd_historial(pos, flags, scrapers, _doc):
    if len(pos) < 2:
        print("Uso: historial <tienda> <nombre_o_id> [--limite N]")
        return
    resultado = _resolver_producto(pos[0], pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    historial = storage.cargar_historial()
    entrada = historial.get(clave)
    if not entrada or not entrada["historial"]:
        print("Este producto todavía no tiene historial registrado.")
        return
    try:
        limite = int(flags.get("limite", 20))
    except ValueError:
        limite = 20
    for registro in entrada["historial"][-limite:]:
        precio = registro.get("precio")
        precio_txt = f"{precio} {registro.get('moneda', '')}" if precio is not None else registro.get("estado")
        print(f"{registro['fecha_hora']}  {precio_txt}")


def cmd_favorito(pos, flags, scrapers, _doc):
    if len(pos) < 3 or pos[2] not in ("on", "off"):
        print("Uso: favorito <tienda> <nombre_o_id> <on|off>")
        return
    resultado = _resolver_producto(pos[0], pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    error = storage.set_favorito(clave, pos[2] == "on")
    if error:
        print(f"Error: {error}")
        return
    print(f"'{producto.get('nombre_producto')}' favorito: {pos[2] == 'on'}.")


def cmd_peso(pos, flags, scrapers, _doc):
    if len(pos) < 3:
        print("Uso: peso <tienda> <nombre_o_id> <0-10>")
        return
    resultado = _resolver_producto(pos[0], pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    try:
        peso = int(pos[2])
    except ValueError:
        print("El peso debe ser un número entero.")
        return
    if peso == 0 and not y_or_n(
        f"Peso 0 saca a '{producto.get('nombre_producto')}' de la cola automática. ¿Continuar? (Y/N): "
    ):
        print("Cancelado.")
        return
    error = storage.set_peso(clave, peso)
    if error:
        print(f"Error: {error}")
        return
    print(f"Peso de '{producto.get('nombre_producto')}' actualizado a {peso}.")


def cmd_umbral(pos, flags, scrapers, _doc):
    if len(pos) < 3:
        print("Uso: umbral <tienda> <nombre_o_id> <precio|off>")
        return
    resultado = _resolver_producto(pos[0], pos[1])
    if resultado is None:
        return
    clave, producto = resultado
    valor = None if pos[2] == "off" else pos[2]
    error = storage.set_umbral(clave, valor)
    if error:
        print(f"Error: {error}")
        return
    print(f"Umbral de '{producto.get('nombre_producto')}' actualizado.")


def cmd_configurar(pos, flags, scrapers, _doc):
    if not pos:
        print("Uso: configurar <telegram|correo|popups>")
        return
    canal = pos[0]
    if canal == "telegram":
        modificar_json("telegram_config", ["token", "chat_id"])
    elif canal == "correo":
        modificar_json("correo_config", ["correo_receptor", "correo_remitente", "contraseña"])
    elif canal == "popups":
        print("Los popups se configuran editando data/user_data.json directamente "
              "(tiempos y radios); aquí solo puedes activarlos/desactivarlos.")
        if y_or_n("¿Activar popups? (Y/N): "):
            config = _leer_config_usuario()
            config.setdefault("popup_config", {})["popup_activado"] = True
            with open(RUTA_USER_DATA, "w", encoding="utf-8") as archivo:
                json.dump(config, archivo, indent=4, ensure_ascii=False)
    else:
        print("Canal no reconocido. Usa: telegram, correo o popups.")


def cmd_limpiar(pos, flags, scrapers, _doc):
    limpiar_datos(confirmar=bool(flags.get("confirmar")))


def cmd_estado(pos, flags, scrapers, _doc):
    config = scheduler.cargar_config_tiendas()
    estado = scheduler.cargar_estado()
    scheduler.resetear_presupuesto_si_corresponde(estado, config)
    filtro = flags.get("tienda")
    for tienda in config.get("tiendas", {}):
        if filtro and tienda != filtro:
            continue
        disponible = scheduler.presupuesto_disponible(tienda, estado, config)
        usados = estado["tiendas"].get(tienda, {}).get("peticiones_usadas_hoy", 0)
        maximo = config["tiendas"][tienda]["peticiones_max_dia"]
        print(f"{tienda}: {usados}/{maximo} usadas hoy, {disponible} disponibles ahora.")
    activo = BACKGROUND_STATE["hilo"] is not None and BACKGROUND_STATE["hilo"].is_alive()
    print(f"Modo segundo plano: {'activo' if activo else 'detenido'}.")


def cmd_probar_conexion(pos, flags, scrapers, _doc):
    tiendas = [pos[0]] if pos else list(scrapers.keys())
    for tienda in tiendas:
        scraper = scrapers.get(tienda)
        if scraper is None:
            print(f"{tienda}: sin implementar todavía.")
            continue
        id_prueba = IDS_PRUEBA.get(tienda)
        if id_prueba is None:
            print(f"{tienda}: scraper cargado, pero no hay id de prueba configurado para verificarlo.")
            continue
        try:
            resultado = scraper.buscar_precio(id_prueba)
            print(f"{tienda}: conexión OK ('{resultado.titulo}' -> {resultado.precio_actual} {resultado.divisa}).")
        except StoreError as e:
            print(f"{tienda}: error de conexión — {e}")
        except Exception as e:
            print(f"{tienda}: error inesperado — {e}")


def cmd_diagnostico(pos, flags, scrapers, _doc):
    archivos = [
        storage.WATCHLIST_PATH, storage.HISTORY_PATH, RUTA_USER_DATA,
        scheduler.STORE_CONFIG_PATH, scheduler.STATE_PATH,
    ]
    for ruta in archivos:
        if not ruta.exists():
            print(f"{ruta}: no existe.")
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                json.load(archivo)
            print(f"{ruta}: OK.")
        except json.JSONDecodeError as e:
            print(f"{ruta}: JSON inválido ({e}).")


def cmd_ayuda(pos, flags, scrapers, doc):
    comandos = doc.get("comandos", {})
    if pos:
        info = comandos.get(pos[0])
        if info is None:
            print(f"No hay ayuda para '{pos[0]}'.")
            return
        print(f"{pos[0]}: {info.get('descripcion')}")
        print(f"  Sintaxis: {info.get('sintaxis')}")
        for ejemplo in info.get("ejemplos", []):
            print(f"  Ej: {ejemplo}")
        return
    print("Comandos disponibles:")
    for nombre, info in comandos.items():
        print(f"  {nombre:<16} {info.get('descripcion', '')[:70]}")
    print("Usa 'ayuda <comando>' para el detalle de uno.")


def cmd_segundo_plano(pos, flags, scrapers, _doc):
    if not pos or pos[0] not in ("iniciar", "detener"):
        print("Uso: segundo_plano <iniciar|detener>")
        return
    if pos[0] == "iniciar":
        iniciar_segundo_plano(scrapers)
    else:
        detener_segundo_plano()


def cmd_salir(pos, flags, scrapers, _doc):
    if BACKGROUND_STATE["hilo"] is not None and BACKGROUND_STATE["hilo"].is_alive():
        if y_or_n("El modo segundo plano está activo. ¿Detenerlo antes de salir? (Y/N): "):
            detener_segundo_plano()
    return True  # señal para romper el loop principal


DESPACHADOR = {
    "agregar": cmd_agregar,
    "quitar": cmd_quitar,
    "borrar": cmd_borrar,
    "listar": cmd_listar,
    "consultar": cmd_consultar,
    "revisar": cmd_revisar,
    "historial": cmd_historial,
    "favorito": cmd_favorito,
    "peso": cmd_peso,
    "umbral": cmd_umbral,
    "configurar": cmd_configurar,
    "limpiar": cmd_limpiar,
    "estado": cmd_estado,
    "probar_conexion": cmd_probar_conexion,
    "diagnostico": cmd_diagnostico,
    "ayuda": cmd_ayuda,
    "segundo_plano": cmd_segundo_plano,
    "salir": cmd_salir,
}


# --- modo segundo plano ---
# Disparador implementado: cada 12h desde medianoche, y al iniciar el
# programa (si está activado en user_data.json). 'al_volver_reposo' y
# 'antes_apagar' quedan pendientes de elegir una librería.

BACKGROUND_STATE = {"hilo": None, "detener": threading.Event()}


def _segundos_hasta_proximo_12h() -> float:
    ahora = datetime.now()
    hoy_00 = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    candidatos = [hoy_00 + timedelta(hours=h) for h in (0, 12, 24)]
    proximo = next(c for c in candidatos if c > ahora)
    return (proximo - ahora).total_seconds()


def _bucle_segundo_plano(scrapers):
    activos = {t: s for t, s in scrapers.items() if s is not None}
    while not BACKGROUND_STATE["detener"].is_set():
        espera = _segundos_hasta_proximo_12h()
        if BACKGROUND_STATE["detener"].wait(espera):
            break
        print("\n[segundo plano] ejecutando revisión programada (disparador: 12h)...")
        try:
            scheduler.ejecutar_pasada(activos)
        except Exception as e:
            print(f"[segundo plano] error durante la revisión: {e}")


def iniciar_segundo_plano(scrapers):
    if BACKGROUND_STATE["hilo"] is not None and BACKGROUND_STATE["hilo"].is_alive():
        print("El modo segundo plano ya está activo.")
        return
    BACKGROUND_STATE["detener"].clear()
    hilo = threading.Thread(target=_bucle_segundo_plano, args=(scrapers,), daemon=True)
    BACKGROUND_STATE["hilo"] = hilo
    hilo.start()
    print("Modo segundo plano iniciado (disparador activo: cada 12h desde medianoche). "
          "'al volver del reposo' y 'antes de apagar' aún no están implementados.")


def detener_segundo_plano():
    if BACKGROUND_STATE["hilo"] is None or not BACKGROUND_STATE["hilo"].is_alive():
        print("El modo segundo plano no está activo.")
        return
    BACKGROUND_STATE["detener"].set()
    print("Deteniendo modo segundo plano...")


# --- loop principal ---

def main():
    print("price_monitor — escribe 'ayuda' para ver los comandos disponibles.")
    comandos_doc = cargar_comandos()
    scrapers = _cargar_scrapers()
    config_usuario = _leer_config_usuario()
    disparadores = config_usuario.get("segundo_plano_config", {}).get("disparadores", {})

    if disparadores.get("al_iniciar_programa"):
        print("[main] disparador 'al iniciar' activo: ejecutando una revisión ahora...")
        activos = {t: s for t, s in scrapers.items() if s is not None}
        if activos:
            scheduler.ejecutar_pasada(activos)

    if config_usuario.get("segundo_plano_config", {}).get("activado"):
        iniciar_segundo_plano(scrapers)

    while True:
        try:
            linea = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break
        if not linea:
            continue
        comando, pos, flags = _parsear(linea)
        if comando is None:
            continue
        manejador = DESPACHADOR.get(comando)
        if manejador is None:
            print(f"Comando no reconocido: '{comando}'. Escribe 'ayuda' para ver la lista.")
            continue
        try:
            salir = manejador(pos, flags, scrapers, comandos_doc)
        except Exception as e:
            print(f"[main] error inesperado ejecutando '{comando}': {e}")
            continue
        if salir:
            break


if __name__ == "__main__":
    main()