# Nota: Define la clase abstracta base para los scrapers de tiendas.
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import optional, List
from datetime import datetime, timezone

class error(Exception):
    """Error genérico al consultar una tienda (red, parseo, producto no encontrado, etc.)"""
    pass

@dataclass
class resultado_precio:
    tienda: str
    id_producto: optional[str]
    id_producto_interno: str
    titulo: str
    precio_actual: float
    precio_anterior: optional[float]
    precio_original: optional[float]
    divisa: str
    oferta: bool
    descuento: optional[float]
    url: str
    timestamp: str #ISO 8601
    disponible: bool #False si no esta disponible (por cualquier motivo)
    agotado: bool #si este y disponible son False dar un error 

class store_scraper(ABC):
    nombre_tienda: str
    @abstractmethod
    def buscar_precio(self, id_producto: str) -> resultado_precio:
        """Devuelve el precio actual de un producto en la tienda"""
        raise NotImplementedError("Este método debe ser implementado por la subclase.")
    def _now(self) ->str:
        # Helper compartido: todas las tiendas timestampean igual
        return datetime.now(timezone.utc).isoformat()