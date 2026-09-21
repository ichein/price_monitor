# price_monitor

```text
price_monitor/
├── core/
│   ├── background.py        # Gestión del segundo plano / scheduler loop
│   ├── notifier.py          # Notificaciones por Telegram, correo y popups
│   ├── scheduler.py         # Presupuesto, colas y balanceo de consultas
│   ├── storage.py           # Persistencia de watchlist e historial
│   ├── store_base.py        # Base abstracta para scrapers
│   └── extras/
│       └── recode.py        # Helpers de entrada, validación y JSON
├── stores/
│   ├── amazon.py            # Placeholder de Amazon
│   ├── eneba.py             # Placeholder de Eneba
│   ├── mercadolibre.py      # Placeholder de Mercado Libre
│   └── steam.py             # Scraper funcional de Steam
├── data/
│   ├── price_history.json   # Historial de precios
│   ├── scheduler_state.json # Estado del planificador
│   ├── user_data.json       # Configuración del usuario
│   └── watchlist.json       # Productos vigilados
├── visuals/
│   ├── configuracion.py     # Pantalla de configuración de la app
│   ├── listas.py            # Listados y vistas de productos
│   ├── visual_historial.py  # Historial visual
│   └── visual_main.py       # Interfaz principal visual
├── style/
│   ├── popup.qss            # Estilo de popups
│   └── visual_main.qss      # Estilo de la interfaz
├── price_monitor/           # Entorno virtual (venv)
├── main.py                  # Punto de entrada principal
├── commands.json            # Comandos y ayuda de la consola
├── store_config.json        # Configuración por tienda
├── README.md                # Documentación del proyecto
├── debug_segundo_plano.py   # Módulo auxiliar de depuración del segundo plano
└── test_commands.py         # Script de validación de comandos del programa
```

## Comandos

Sintaxis: `comando argumentos [--opciones]`. Los comandos se definen en `commands.json`.
Los argumentos con espacios deben escribirse entre comillas. En comandos sobre productos ya agregados, `<nombre_o_id>` acepta coincidencias parciales dentro de la tienda indicada; si hay varias, se debe usar el nombre o ID exacto.

- `agregar`: añade un producto a la watchlist.
- `quitar`: desactiva un producto sin borrar su historial.
- `borrar`: elimina un producto y su historial.
- `listar`: muestra los productos vigilados.
- `consultar`: realiza una consulta manual.
- `revisar`: ejecuta una pasada del scheduler.
- `historial`: muestra el historial de precios.
- `favorito`: activa o desactiva un favorito.
- `peso`: cambia la prioridad de un producto.
- `umbral`: configura o elimina un precio de aviso.
- `configurar`: configura Telegram, correo o popups.
- `limpiar`: elimina las credenciales de notificación.
- `segundo_plano`: inicia o detiene las revisiones automáticas.
- `estado`: muestra el estado del scheduler y el presupuesto.
- `probar_conexion`: prueba la conexión de una o todas las tiendas sin guardar datos.
- `diagnostico`: revisa los archivos JSON principales sin modificarlos.
- `ayuda`: muestra la ayuda disponible.
- `salir`: cierra el programa.

## Datos devueltos por los scrapers

Cada scraper debe implementar `buscar_precio(id_producto)` y devolver un `resultado_precio` definido en `core/store_base.py`.

| Campo | Requisito |
| --- | --- |
| `tienda` | Nombre interno de la tienda. |
| `id_producto` | Identificador recibido por el scraper. Puede ser `None`. |
| `id_producto_interno` | ID estable usado para guardar el historial. |
| `titulo` | Nombre del producto. |
| `precio_actual` | Precio numérico o `None` si no está disponible. |
| `precio_original` | Precio anterior al descuento o `None`. |
| `divisa` | Código de moneda, por ejemplo `MXN` o `USD`. |
| `oferta` | `True` si existe descuento. |
| `descuento` | Porcentaje numérico o `None`. |
| `url` | URL del producto. |
| `timestamp` | Fecha ISO 8601 con zona horaria. |
| `estado` | `DISPONIBLE`, `AGOTADO`, `SIN_PRECIO_REGION` o `NO_ENCONTRADO`. |
| `precio_anterior` | Precio previo conocido o `None`. |

Los campos deben conservar estos nombres y tipos. Para estados sin precio, `precio_actual` debe ser `None`.

## Checklist 

- [ ] `stores/amazon.py`
- [ ] `stores/mercadolibre.py`
- [ ] `stores/eneba.py`
- [ ] `visuals/visual_main.py`
- [ ] `visuals/visual_historial.py`
- [ ] `core/background.py`

