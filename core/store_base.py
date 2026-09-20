# Base para scrapers de tiendas.
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum

class error(Exception):
    """Error genérico al consultar una tienda."""
    pass

# Compatibilidad del nombre del enum en todo el proyecto.
class EstadoProducto(Enum):
    DISPONIBLE = "disponible"
    AGOTADO = "agotado"
    SIN_PRECIO_REGION = "sin_precio_region"
    NO_ENCONTRADO = "no_encontrado"

@dataclass
class resultado_precio:
    tienda: str
    id_producto: Optional[str]
    id_producto_interno: str
    titulo: str
    # CORREGIDO puede ser None (SIN_PRECIO_REGION, AGOTADO, ...)
    precio_actual: Optional[float]
    precio_original: Optional[float]
    divisa: str
    oferta: bool
    descuento: Optional[float]
    url: str
    timestamp: str  # ISO 8601, hora local con offset (ej. 2026-09-19T06:34:56-06:00)
    estado: EstadoProducto
    # CORREGIDO antes era obligatorio y steam.py nunca lo pasaba -> TypeError.
    precio_anterior: Optional[float] = None


class store_scraper(ABC):
    nombre_tienda: str
    @abstractmethod
    def buscar_precio(self, id_producto: str) -> resultado_precio:
        """Devuelve el precio actual de un producto en la tienda"""
        raise NotImplementedError("Este método debe ser implementado por la subclase.")
    def _now(self) -> str:
        # Helper compartido: todas las tiendas timestampean igual.
        # CORREGIDO  antes era UTC con microsegundos; ahora es la hora local del sistema (con su offset, así sigue siendo ISO 8601 sin ambigüedad).
        return datetime.now().astimezone().isoformat(timespec="seconds")