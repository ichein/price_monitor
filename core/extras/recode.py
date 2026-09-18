# funciones que repito mucho
import json
import shutil
import threading
import queue
from pathlib import Path
from typing import Optional


def y_or_n(prompt: str = "¿Confirmas? (Y/N): ") -> bool:
    # Pregunta sí/no.
    aceptados = {"y", "yes", "s", "si", "sí"}
    respuesta = input(prompt).strip().lower()
    return respuesta in aceptados


def input_con_timeout(prompt: str, timeout: int = 10) -> Optional[str]:
    # input() con límite de tiempo. Devuelve None si no hubo respuesta dentro de `timeout`
    resultado = queue.Queue()
    def _leer():
        try:
            resultado.put(input(prompt))
        except EOFError:
            resultado.put(None)
    hilo = threading.Thread(target=_leer, daemon=True)
    hilo.start()
    hilo.join(timeout)
    if hilo.is_alive():
        print("\nTiempo de espera agotado. Configuración cancelada.")
        return None
    return resultado.get()


def modificar_json(campo: str, llaves: list[str], timeout: int = 10) -> Optional[dict]:
    """Valida que `campo` y cada llave de `llaves` existan en user_data.json,
    y si es correcto, pide al usuario un valor para cada llave (con
    timeout) y guarda los cambios. Devuelve el dict {llave: valor} recién
    guardado, o None si algo falló o el usuario no respondió a tiempo."""
    with open("data/user_data.json", "r", encoding="utf-8") as archivo:
        config = json.load(archivo)
    if campo not in config:
        print(f"error de sistema: la sección '{campo}' no existe en user_data.json")
        return None
    claves_invalidas = [k for k in llaves if k not in config[campo]]
    if claves_invalidas:
        print(f"error de sistema: claves no reconocidas en '{campo}': {claves_invalidas}")
        return None
    valores = {}
    for llave in llaves:
        valor = input_con_timeout(f"{llave}: ", timeout=timeout)
        if valor is None:
            print("Configuración cancelada.")
            return None
        valores[llave] = valor
    config[campo].update(valores)
    with open("data/user_data.json", "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, indent=4, ensure_ascii=False)
    return valores


def limpiar_datos():
    if not y_or_n("¿Deseas limpiar todos los datos? (Y/N): "):
        print("Limpieza cancelada.")
        return
    with open("data/user_data.json", "r", encoding="utf-8") as archivo:
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
    with open("data/user_data.json", "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, indent=4, ensure_ascii=False)
    # extras/ -> core/ -> raíz del proyecto (dos niveles, no uno)
    directorio_proyecto = Path(__file__).resolve().parent.parent.parent
    for directorio_cache in directorio_proyecto.rglob("__pycache__"):
        if directorio_cache.is_dir():
            shutil.rmtree(directorio_cache)
    print("Datos y cache de Python limpiados correctamente.")