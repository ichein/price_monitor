# Lógica de Steam.
import sys
from pathlib import Path

# Permite ejecutar como script.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from typing import Optional

from core.store_base import store_scraper, resultado_precio, EstadoProducto, error

BUSQUEDA_URL = "https://store.steampowered.com/api/storesearch"
DETALLES_URL = "https://store.steampowered.com/api/appdetails"

# Códigos ISO 4217 por país.
MONEDA_POR_PAIS = {
    "mx": "MXN", "us": "USD", "ca": "CAD", "br": "BRL", "ar": "ARS", "cl": "CLP",
    "co": "COP", "pe": "PEN", "uy": "UYU", "gb": "GBP", "jp": "JPY", "au": "AUD",
    "es": "EUR", "de": "EUR", "fr": "EUR", "it": "EUR", "pt": "EUR", "nl": "EUR",
}


class steam_scraper(store_scraper):
    nombre_tienda = "steam"

    def __init__(self, country_code: str = "mx", idioma: str = "spanish", timeout: int = 10):
        self.cc = country_code
        self.idioma = idioma
        self.timeout = timeout
        self.divisa_region = MONEDA_POR_PAIS.get(country_code.lower(), country_code.upper())

    def buscar_precio(self, id_producto: str) -> resultado_precio:
        identificador = str(id_producto).strip()
        if identificador.isdigit():
            appid = identificador
        else:
            appid = self._resolver_appid_por_nombre(identificador)
        return self._consultar_appdetails(appid, id_producto_original=identificador)

    # Resolución por nombre.
    def _resolver_appid_por_nombre(self, nombre: str) -> str:
        try:
            respuesta = requests.get(
                BUSQUEDA_URL,
                params={"term": nombre, "cc": self.cc, "l": self.idioma},
                timeout=self.timeout,
                headers={"User-Agent": "monitor-precios/1.0"},
            )
            respuesta.raise_for_status()
        except requests.RequestException as e:
            raise error(f"[steam] fallo de red buscando '{nombre}': {e}")
        try:
            datos = respuesta.json()
        except ValueError as e:
            raise error(f"[steam] respuesta no-JSON buscando '{nombre}': {e}")
        items = datos.get("items", [])
        if not items:
            raise error(f"[steam] nombre incorrecto o inexistente: '{nombre}'")
        return str(items[0]["id"])

    # Consulta por appid.
    def _consultar_appdetails(self, appid: str, id_producto_original: str) -> resultado_precio:
        try:
            respuesta = requests.get(
                DETALLES_URL,
                params={"appids": appid, "cc": self.cc, "l": self.idioma},
                timeout=self.timeout,
                headers={"User-Agent": "monitor-precios/1.0"},
            )
            respuesta.raise_for_status()
        except requests.RequestException as e:
            raise error(f"[steam] fallo de red consultando appid {appid}: {e}")
        try:
            payload = respuesta.json()
        except ValueError as e:
            raise error(f"[steam] respuesta no-JSON para appid {appid}: {e}")
        entrada = payload.get(appid)
        if entrada is None or not entrada.get("success"):
            raise error(f"[steam] nombre incorrecto o inexistente: appid {appid} no válido")
        data = entrada.get("data", {})
        titulo = data.get("name", f"appid:{appid}")
        url = f"https://store.steampowered.com/app/{appid}/"
        price_overview = data.get("price_overview")
        es_gratis = data.get("is_free", False)
        if price_overview is None:
            if es_gratis:
                return resultado_precio(
                    tienda=self.nombre_tienda,
                    id_producto=id_producto_original,
                    id_producto_interno=appid,
                    titulo=titulo,
                    precio_actual=0.0,
                    precio_anterior=None,
                    precio_original=0.0,
                    divisa=self.divisa_region,
                    oferta=False,
                    descuento=0,
                    url=url,
                    timestamp=self._now(),
                    estado=EstadoProducto.DISPONIBLE,
                )
            return resultado_precio(
                tienda=self.nombre_tienda,
                id_producto=id_producto_original,
                id_producto_interno=appid,
                titulo=titulo,
                precio_actual=None,
                precio_anterior=None,
                precio_original=None,
                divisa=self.divisa_region,
                oferta=False,
                descuento=None,
                url=url,
                timestamp=self._now(),
                estado=EstadoProducto.SIN_PRECIO_REGION,
            )
        return resultado_precio(
            tienda=self.nombre_tienda,
            id_producto=id_producto_original,
            id_producto_interno=appid,
            titulo=titulo,
            precio_actual=price_overview["final"] / 100,
            precio_anterior=None,
            precio_original=price_overview["initial"] / 100,
            divisa=price_overview["currency"],
            oferta=price_overview["discount_percent"] > 0,
            descuento=price_overview["discount_percent"],
            url=url,
            timestamp=self._now(),
            estado=EstadoProducto.DISPONIBLE,
        )

if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Counter-Strike 2"
    scraper = steam_scraper()
    try:
        resultado = scraper.buscar_precio(entrada)
        print(resultado)
    except error as e:
        print(f"nombre incorrecto o inexistente: {e}")