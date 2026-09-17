# price_monitor

price_monitor/
├── core/
│   ├── store_base.py        # Clase abstracta StoreScraper
│   ├── scheduler.py         # Lógica de horarios aleatorios / pesos
│   ├── storage.py           # Leer/escribir JSON, historial de precios
│   └── notifier.py          # Envío de avisos por correo y ventanas emergentes
├── stores/
│   ├── steam.py             # Implementación concreta para Steam
│   ├── amazon.py            # (v2, vacío por ahora)
│   └── mercadolibre.py      # (v2, vacío por ahora)
├── data/
│   ├── watchlist.json       # Lista de productos que deben vigilarse
│   ├── user_data.json       # Configuración de Telegram, correo y popups
│   └── history/
│       └── README.md        # Descripción del historial de precios
├── style/
│   ├── popup.qss            # Estilos visuales de las ventanas emergentes
│   └── visual_main.qss      # Hoja de estilos para la interfaz visual de la v2
├── config.json              # Configuración general del monitor
├── main.py                  # Punto de entrada y coordinación de la aplicación
├── visual_main.py           # Capa de personalización y manejo visual de main.py para la v2
└── README.md                # Documentación y estructura del proyecto

## Checklist


- [x] `core/store_base.py`
- [ ] `core/scheduler.py`
- [ ] `core/storage.py`
- [x] `core/notifier.py`

- [ ] `stores/steam.py`
- [ ] `stores/amazon.py`
- [ ] `stores/mercadolibre.py`

- [ ] `data/watchlist.json`
- [ ] `data/user_data.json`
- [ ] `data/history/README.md`

- [ ] `style/popup.qss`
- [ ] `style/visual_main.qss`
- [ ] `config.json`


- [ ] `main.py`
- [ ] `visual_main.py`
- [ ] `README.md`

