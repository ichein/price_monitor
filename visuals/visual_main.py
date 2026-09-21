# visuals/visual_main.py
# Ventana principal PyQt6: solo la pestaña de buscar/agregar productos y
# hacer peticiones. Configuración y listados viven en archivos propios
# (configuracion.py, listas.py) y se importan aquí como pestañas.

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QPushButton, QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core import storage, scheduler, notifier
from core.extras.recode import RAIZ_PROYECTO

from visuals.configuracion import TabConfiguracion
from visuals.listas import TabVigilados

QSS_PATH = RAIZ_PROYECTO / "style" / "visual_main.qss"

import main as consola  # noqa: E402  (import tras sys.path.insert)


class TabBuscarAgregar(QWidget):
    def __init__(self, scrapers: dict, parent=None):
        super().__init__(parent)
        self.scrapers = scrapers

        self.combo_tienda = QComboBox()
        self.combo_tienda.addItems(sorted(scrapers.keys()))
        self.campo_id = QLineEdit()
        self.campo_id.setPlaceholderText("Nombre o id del producto")
        self.spin_peso = QSpinBox()
        self.spin_peso.setRange(0, 10)
        self.spin_peso.setValue(1)
        self.campo_umbral = QLineEdit()
        self.campo_umbral.setPlaceholderText("Umbral de aviso (opcional)")

        boton_agregar = QPushButton("Agregar a vigilados")
        boton_agregar.clicked.connect(self._agregar)
        boton_consultar = QPushButton("Consultar ahora (sin agregar)")
        boton_consultar.clicked.connect(self._consultar)
        boton_revisar = QPushButton("Revisar todo ahora")
        boton_revisar.clicked.connect(self._revisar)

        form = QFormLayout()
        form.addRow("Tienda:", self.combo_tienda)
        form.addRow("Producto:", self.campo_id)
        form.addRow("Peso:", self.spin_peso)
        form.addRow("Umbral:", self.campo_umbral)

        fila_botones = QHBoxLayout()
        fila_botones.addWidget(boton_agregar)
        fila_botones.addWidget(boton_consultar)
        fila_botones.addWidget(boton_revisar)

        self.salida = QTextEdit()
        self.salida.setReadOnly(True)

        self.lista_avisos = QListWidget()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(fila_botones)
        layout.addWidget(QLabel("Salida:"))
        layout.addWidget(self.salida)
        layout.addWidget(QLabel("Avisos (ofertas / cruces de umbral):"))
        layout.addWidget(self.lista_avisos)

        if not scrapers:
            self.combo_tienda.setEnabled(False)
            self._log("No hay ninguna tienda con scraper implementado todavía.")

    def _log(self, texto: str):
        self.salida.append(texto)

    def _scraper_actual(self):
        tienda = self.combo_tienda.currentText()
        return tienda, self.scrapers.get(tienda)

    def _agregar(self):
        tienda, scraper = self._scraper_actual()
        entrada = self.campo_id.text().strip()
        if not entrada:
            self._log("Escribe un nombre o id antes de agregar.")
            return
        umbral = self.campo_umbral.text().strip() or None
        try:
            clave = storage.agregar_producto(
                tienda, entrada, entrada, peso=self.spin_peso.value(), umbral_aviso=umbral,
            )
            self._log(f"Agregado ({tienda}): '{entrada}' -> clave interna {clave}")
        except ValueError as e:
            self._log(f"Error: {e}")

    def _consultar(self):
        tienda, scraper = self._scraper_actual()
        if scraper is None:
            self._log(f"'{tienda}' no tiene scraper implementado todavía.")
            return
        entrada = self.campo_id.text().strip()
        if not entrada:
            self._log("Escribe un nombre o id antes de consultar.")
            return
        coincidencias = storage._buscar_productos(tienda, entrada)
        if len(coincidencias) == 1:
            clave, producto = coincidencias[0]
            id_real = producto.get("id_producto_interno") or producto.get("id_producto")
        else:
            clave, id_real = f"{tienda}:tmp-consulta-directa", entrada
        try:
            resultado = scraper.buscar_precio(id_real)
        except Exception as e:
            self._log(f"Error consultando: {e}")
            return
        self._log(f"{resultado.titulo}: {resultado.precio_actual} {resultado.divisa} "
                   f"(estado: {resultado.estado.value})")

    def _revisar(self):
        activos = {t: s for t, s in self.scrapers.items() if s is not None}
        if not activos:
            self._log("No hay tiendas activas para revisar.")
            return
        resumen = scheduler.ejecutar_pasada(activos)
        self._log(f"Revisión completa: {len(resumen['atendidos'])} consultados, "
                   f"{len(resumen['ofertas'])} con oferta, {len(resumen['umbral_cruzado'])} con umbral cruzado.")
        self.lista_avisos.clear()
        watchlist = storage.cargar_watchlist()
        for clave in set(resumen["ofertas"]) | set(resumen["umbral_cruzado"]):
            producto = watchlist.get(clave, {})
            nombre = producto.get("nombre_producto", clave)
            etiqueta = []
            if clave in resumen["ofertas"]:
                etiqueta.append("bajó de precio")
            if clave in resumen["umbral_cruzado"]:
                etiqueta.append("cruzó umbral")
            self.lista_avisos.addItem(f"{nombre} — {', '.join(etiqueta)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("price_monitor")
        self.resize(900, 650)

        scrapers = consola._cargar_scrapers()

        pestañas = QTabWidget()
        pestañas.addTab(TabBuscarAgregar(scrapers), "Buscar / Agregar")
        pestañas.addTab(TabConfiguracion(), "Configuración")
        pestañas.addTab(TabVigilados(), "Vigilados")
        self.setCentralWidget(pestañas)

        try:
            with open(QSS_PATH, "r", encoding="utf-8") as archivo:
                self.setStyleSheet(archivo.read())
        except FileNotFoundError:
            print(f"[visual_main] no se encontró {QSS_PATH}; se usa el estilo por defecto de Qt.")


def iniciar_gui():
    app = notifier._get_app()
    ventana = MainWindow()
    ventana.show()
    app.exec()


if __name__ == "__main__":
    iniciar_gui()