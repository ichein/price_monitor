# price_monitor

```text
price_monitor/
├── core/
│   ├── store_base.py        # Base abstracta para scrapers
│   ├── scheduler.py         # Presupuesto, colas y balanceo de consultas
│   ├── storage.py           # Persistencia de watchlist e historial
│   ├── notifier.py          # Notificaciones por Telegram, correo y popups
│   └── extras/
│       └── recode.py        # Helpers de entrada, validación y JSON
├── stores/
│   ├── steam.py             # Scraper funcional de Steam
│   ├── amazon.py            # Placeholder de Amazon
│   └── mercadolibre.py      # Placeholder de Mercado Libre
├── data/
│   ├── watchlist.json       # Productos vigilados
│   ├── user_data.json       # Configuración del usuario
│   ├── scheduler_state.json  # Estado del planificador
│   └── price_history.json   # Historial de precios
├── visuals/
│   ├── visual_main.py       # Interfaz principal visual
│   └── visual_historial.py  # Historial visual
├── style/
│   ├── popup.qss            # Estilo de popups
│   └── visual_main.qss      # Estilo de la interfaz
├── main.py                  # Punto de entrada principal
├── commands.json            # Comandos y ayuda de la consola
├── store_config.json        # Configuración por tienda
└── README.md                # Documentación del proyecto
```

## Comandos

Sintaxis: `comando argumentos [--opciones]`. Los comandos se definen en `commands.json`.

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
- `ayuda`: muestra la ayuda disponible.
- `salir`: cierra el programa.

## Checklist

- [x] `core/store_base.py`
- [x] `core/scheduler.py`
- [x] `core/storage.py`
- [x] `core/notifier.py`
- [x] `core/extras/recode.py`
- [x] `stores/steam.py`
- [ ] `stores/amazon.py`
- [ ] `stores/mercadolibre.py`
- [x] `data/watchlist.json`
- [x] `data/user_data.json`
- [x] `data/scheduler_state.json`
- [x] `data/price_history.json`
- [ ] `visuals/visual_main.py`
- [ ] `visuals/visual_historial.py`
- [x] `style/popup.qss`
- [x] `style/visual_main.qss`
- [ ] `main.py`
- [x] `commands.json`
- [x] `store_config.json`
- [ ] `README.md`

