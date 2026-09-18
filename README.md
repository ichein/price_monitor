# price_monitor

```text
price_monitor/
├── core/
│   ├── store_base.py        # Clase abstracta StoreScraper
│   ├── scheduler.py         # Pendiente: lógica de horarios aleatorios / pesos
│   ├── storage.py           # Pendiente: leer/escribir JSON e historial de precios
│   ├── notifier.py          # Envío de avisos por correo y ventanas emergentes
│   └── extras/
│       └── recode.py        # Funciones auxiliares
├── stores/
│   ├── steam.py             # Implementación concreta para Steam
│   ├── amazon.py            # (v2, vacío por ahora)
│   └── mercadolibre.py      # (v2, vacío por ahora)
├── data/
│   ├── watchlist.json       # Lista de productos que deben vigilarse
│   ├── user_data.json       # Configuración de Telegram, correo y popups
│   └── history/             # Historial de precios (pendiente de implementar)
├── style/
│   ├── popup.qss            # Estilos visuales de las ventanas emergentes
│   └── visual_main.qss      # Hoja de estilos para la interfaz visual
├── store_config.json        # Configuración de las tiendas disponibles
├── main.py                  # Pendiente: punto de entrada y coordinación de la aplicación
├── pruebas.py               # Pruebas aisladas
├── visuals/
│   └── visual_main.py       # Placeholder para la interfaz visual
└── README.md                # Documentación y estructura del proyecto
```

## Checklist

- [x] `core/store_base.py`
- [ ] `core/scheduler.py`
- [ ] `core/storage.py`
- [x] `core/notifier.py`
- [x] `stores/steam.py`
- [ ] `stores/amazon.py`
- [ ] `stores/mercadolibre.py`
- [ ] `data/watchlist.json`
- [ ] `data/user_data.json`
- [ ] `style/popup.qss`
- [ ] `style/visual_main.qss`
- [ ] `store_config.json`
- [ ] `main.py`
- [ ] `visuals/visual_main.py`
- [ ] `README.md`

