# price_monitor

monitor-precios/
├── core/
│   ├── store_base.py        # Clase abstracta StoreScraper
│   ├── scheduler.py         # Lógica de horarios aleatorios / pesos
│   ├── storage.py           # Leer/escribir JSON, historial de precios
│   └── notifier.py          # Envío de avisos (consola, Telegram, email...)
├── stores/
│   ├── steam.py             # Implementación concreta para Steam
│   ├── amazon.py            # (v2, vacío por ahora)
│   └── mercadolibre.py      # (v2, vacío por ahora)
├── data/
│   ├── watchlist.json       # Qué productos vigilar
│   └── history/             # Historial de precios por producto
├── config.json               # Intervalos, umbrales de oferta, pesos por tienda
└── main.py                   # Orquestador: recorre watchlist y llama al store correcto