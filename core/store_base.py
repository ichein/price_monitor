# Nota: Define la clase abstracta base para los scrapers de tiendas.
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
from enum import Enum

class error(Exception):
    """Error genérico al consultar una tienda (red, parseo, producto no encontrado, etc.)"""
    pass

class estado_producto(Enum):
    DISPONIBLE = "disponible"               # se puede comprar
    AGOTADO = "agotado"                     # existe, sin stock
    SIN_PRECIO_REGION = "sin_precio_region" # existe pero no se vende en el cc/región consultada
    NO_ENCONTRADO = "no_encontrado"         # el id/nombre no existe

@dataclass
class resultado_precio:
    tienda: str
    id_producto: Optional[str]
    id_producto_interno: str
    titulo: str
    precio_actual: float
    precio_anterior: Optional[float]
    precio_original: Optional[float]
    divisa: str
    oferta: bool
    descuento: Optional[float]
    url: str
    timestamp: str #ISO 8601
    estado: estado_producto

class store_scraper(ABC):
    nombre_tienda: str
    @abstractmethod
    def buscar_precio(self, id_producto: str) -> resultado_precio:
        """Devuelve el precio actual de un producto en la tienda"""
        raise NotImplementedError("Este método debe ser implementado por la subclase.")
    def _now(self) ->str:
        # Helper compartido: todas las tiendas timestampean igual
        return datetime.now(timezone.utc).isoformat()