#funciones que repito mucho
from typing import Any, Dict, List, Optional
import json

def y_or_n():
    acept = ["y","Y","yes","Yes","YES","s","S","si"]
    yes_or_not = imput("¿Deseas limpiar todos los datos? (Y/N): ").strip().lower()
    if yes_or_not not in (acept):
        return True
    else:
        return False

def limpiar_datos():
    confirmar = y_or_n()
    if confirmar is not True:
        print("Limpieza cancelada.")
        return
    else:
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
        directorio_proyecto = Path(__file__).resolve().parent.parent
        for directorio_cache in directorio_proyecto.rglob("__pycache__"):
            if directorio_cache.is_dir():
                shutil.rmtree(directorio_cache)
        print("Datos y cache de Python limpiados correctamente.")

def comprovaciones(comprovacion: Any, peso: int, llave_valor: str) -> bool:
    with open("data/user_data.json", "r") as archivo:
        config = json.load(archivo)
    if peso not in (0, 1):
        raise ValueError("peso debe ser 0 o 1")
    if llave_valor not in ("llave", "valor"):
        raise ValueError("la comprobacion debe ser 'llave' o 'valor'")
    def recorrer_json(dato: Any):
        yield dato
        if isinstance(dato, dict):
            for clave, valor in dato.items():
                yield clave
                yield from recorrer_json(valor)
        elif isinstance(dato, list):
            for valor in dato:
                yield from recorrer_json(valor)
    if llave_valor == "llave":
        claves_json = {
            elemento
            for elemento in recorrer_json(config)
            if isinstance(elemento, str)
        }
        elementos = comprovacion if isinstance(comprovacion, list) else [comprovacion]
        resultado = all(llave in claves_json for llave in elementos)
    else:
        valores_json = list(recorrer_json(config))
        elementos = comprovacion if isinstance(comprovacion, list) else [comprovacion]
        resultado = all(valor in valores_json for valor in elementos)
    if not resultado:
        print(f"error de sistema: {llave_valor} no existe en user_data.json")
    return resultado

def comprovar_listas(llaves: list[str], valores: list[Any]) -> bool:
    with open("data/user_data.json", "r") as archivo:
        config = json.load(archivo)
    if len(valores) > len(llaves):
        print("error desconocido, mayor numero de variaables que de llaves")
        raise SystemExit(1)
    if len(valores) < len(llaves):
        valores.extend([None] * (len(llaves) - len(valores)))
    configuracion_json = next(
        (
            configuracion
            for configuracion in config.values()
            if isinstance(configuracion, dict)
            and len(configuracion) == len(llaves)
            and set(configuracion) == set(llaves)
        ),
        None,
    )
    if configuracion_json is None:
        print("error de sistema: las llaves no coinciden con user_data.json")
        return False
    llaves_json = list(configuracion_json.keys())
    valores_json = list(configuracion_json.values())
    variable_ejemplo = len(llaves) == len(valores)
    if not variable_ejemplo:
        return False
    if llaves != llaves_json:
        return False
    for valor, valor_json in zip(valores, valores_json):
        if valor is not None and type(valor) is not type(valor_json):
            return False
    return True





def modificar_json(campo: str, llaves: list[str], valores: list[all]):
    llave_externa = comprovaciones(campo,0,"llave")
    llave_interna = comprovaciones(llaves,1,"llave")
    valor_interno = comprovaciones(valores,1,"valor")
    comprovacion_dic = comprovar_listas(llaves, valores)
    if comprovacion_dic == False:
        try:
            with open("data/user_data.json", "r") as archivo:
                config = json.load(archivo)
            configuracion_json = config[campo]
            valores_por_llave = dict(zip(llaves, valores))
            valores_reordenados = [
                valores_por_llave[llave]
                for llave in configuracion_json
                if llave in valores_por_llave
            ]
            if valores_reordenados == valores:
                raise ValueError("no se puede corregir el orden de los valores")
            valores[:] = valores_reordenados
            llaves[:] = list(configuracion_json.keys())
            return modificar_json(campo, llaves, valores)
        except (KeyError, ValueError):
            print("error de llaves y valores")
            print("imposible hacer el reacomodo autmoatico")
            print("se reinica cada valor al predertminado")
            limpiar_datos()
            modificar_json(campo,llaves,valores) 
    elif llave_externa and comprovacion_dic == True:
        return True


#prueva


# modificar_json(campo,llaves,valores,)
# las variables "campo,llaves,valores" son necesarias para la funcion