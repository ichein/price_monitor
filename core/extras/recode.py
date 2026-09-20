# Utilidades reutilizables (genéricas, sin conocer watchlist/historial).
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

# Rutas del proyecto.
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
RUTA_USER_DATA = RAIZ_PROYECTO / "data" / "user_data.json"

# Bandera de activación por sección.
ACTIVADORES = {
    "telegram_config": "telegram_activado",
    "correo_config": "correo_activado",
}

def _cargar_json(ruta: Path) -> dict:
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _guardar_json(ruta: Path, datos: dict) -> None:
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def y_or_n(prompt: str = "¿Confirmas? (Y/N): ") -> bool:
    aceptados = {"y", "yes", "s", "si", "sí"}
    try:
        respuesta = input(prompt).strip().lower()
    except EOFError:
        return False
    return respuesta in aceptados


# Entrada con timeout.

def _leer_linea_posix(timeout: float) -> Optional[str]:
    """Linux/macOS. None si se agotó el tiempo."""
    import select
    try:
        listo, _, _ = select.select([sys.stdin], [], [], timeout)
    except (OSError, ValueError):
        # stdin sin descriptor real (IDLE, algunos IDEs): no se puede medir el
        # tiempo, pero hay una persona delante; se lee sin límite.
        return input()
    if not listo:
        return None
    linea = sys.stdin.readline()
    if linea == "":
        raise EOFError
    return linea.rstrip("\r\n")


def _leer_linea_windows(timeout: float) -> Optional[str]:
    """Consola de Windows."""
    import msvcrt
    limite = time.monotonic() + timeout
    escritos = []
    while time.monotonic() < limite:
        if not msvcrt.kbhit():
            time.sleep(0.02)
            continue
        tecla = msvcrt.getwch()  # sin eco: el eco se hace a mano
        if tecla in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(escritos)
        if tecla == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
        if tecla in ("\x00", "\xe0"):  # tecla especial (flechas, F1...): descartar el 2º código
            msvcrt.getwch()
            continue
        if tecla == "\b":  # retroceso
            if escritos:
                escritos.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if tecla >= " ":
            escritos.append(tecla)
            sys.stdout.write(tecla)
            sys.stdout.flush()
    return None


def input_con_timeout(prompt: str, timeout: int = 10) -> Optional[str]:
    if sys.stdin is None or sys.stdin.closed:
        print("No hay entrada de teclado disponible. Configuración cancelada.")
        return None
    print(prompt, end="", flush=True)
    try:
        if os.name == "nt" and sys.stdin.isatty():
            valor = _leer_linea_windows(timeout)
        else:
            valor = _leer_linea_posix(timeout)
    except EOFError:
        print("\nEntrada cerrada. Configuración cancelada.")
        return None
    if valor is None:
        print("\nTiempo de espera agotado. Configuración cancelada.")
    return valor


# Validación y conversión de user_data.json.

def _conv_token(texto: str) -> str:
    if re.fullmatch(r"\d+:[A-Za-z0-9_-]{30,}", texto):
        return texto
    raise ValueError("el token de Telegram debe verse como 123456789:AAE... (lo entrega @BotFather)")


def _conv_chat_id(texto: str):
    if re.fullmatch(r"-?\d+", texto):
        return int(texto)
    if re.fullmatch(r"@\w{4,}", texto):
        return texto
    raise ValueError("el chat_id debe ser un número (o @nombre_de_canal)")


def _conv_correo(texto: str) -> str:
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", texto):
        return texto
    raise ValueError("no parece un correo válido")


_CONVERSORES = {
    "token": _conv_token,
    "chat_id": _conv_chat_id,
    "correo_remitente": _conv_correo,
    "correo_receptor": _conv_correo,
}


def convertir_valor_config(llave: str, valor):
    """Normaliza y valida un valor de configuración."""
    if valor is None:
        raise ValueError("el valor está vacío")
    texto = str(valor).strip()
    if not texto:
        raise ValueError("el valor está vacío")
    conversor = _CONVERSORES.get(llave)
    return conversor(texto) if conversor else texto


def valor_config_valido(llave: str, valor) -> bool:
    try:
        convertir_valor_config(llave, valor)
        return True
    except ValueError:
        return False


def modificar_json(campo: str, llaves: list[str], timeout: int = 10, max_intentos: int = 3) -> Optional[dict]:
    """Valida y guarda la configuración pedida al usuario."""
    try:
        with open(RUTA_USER_DATA, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
    except FileNotFoundError:
        print(f"error de sistema: no existe {RUTA_USER_DATA}")
        return None
    except json.JSONDecodeError as e:
        print(f"error de sistema: user_data.json no es un JSON válido ({e})")
        return None
    if campo not in config:
        print(f"error de sistema: la sección '{campo}' no existe en user_data.json")
        return None
    claves_invalidas = [k for k in llaves if k not in config[campo]]
    if claves_invalidas:
        print(f"error de sistema: claves no reconocidas en '{campo}': {claves_invalidas}")
        return None
    valores = {}
    for llave in llaves:
        for _ in range(max_intentos):
            texto = input_con_timeout(f"{llave}: ", timeout=timeout)
            if texto is None:
                print("Configuración cancelada.")
                return None
            try:
                valores[llave] = convertir_valor_config(llave, texto)
                break
            except ValueError as e:
                print(f"Valor no válido: {e}")
        else:
            print("Demasiados intentos inválidos. Configuración cancelada.")
            return None
    config[campo].update(valores)
    activador = ACTIVADORES.get(campo)
    if activador is not None:
        datos = [k for k in config[campo] if k != activador]
        if all(valor_config_valido(k, config[campo][k]) for k in datos):
            config[campo][activador] = True
    with open(RUTA_USER_DATA, "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, indent=4, ensure_ascii=False)
    return valores


def limpiar_datos():
    if not y_or_n("¿Deseas limpiar todos los datos? (Y/N): "):
        print("Limpieza cancelada.")
        return
    with open(RUTA_USER_DATA, "r", encoding="utf-8") as archivo:
        config = json.load(archivo)
    config["telegram_config"] = {
        "telegram_activado": False,
        "token": None,
        "chat_id": None,
    }
    config["correo_config"] = {
        "correo_activado": False,
        "correo_remitente": None,
        "correo_receptor": None,
        "contraseña": None,
    }
    config.setdefault("popup_config", {})["popup_activado"] = False
    with open(RUTA_USER_DATA, "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, indent=4, ensure_ascii=False)
    for directorio_cache in RAIZ_PROYECTO.rglob("__pycache__"):
        if directorio_cache.is_dir():
            shutil.rmtree(directorio_cache)
    print("Datos y cache de Python limpiados correctamente.")