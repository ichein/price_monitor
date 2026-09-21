# visuals/listas.py
# Ventana/pestaña de listados: productos vigilados por tienda, con peso y
# umbral editables directo en la tabla, e historial de precios del
# producto seleccionado. Puede abrirse sola o incrustarse en visual_main.py.

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core import storage
from core.extras.recode import RAIZ_PROYECTO

QSS_PATH = RAIZ_PROYECTO / "style" / "visual_main.qss"

TIENDAS_CONOCIDAS = ("steam", "amazon", "mercadolibre", "eneba")


class TabVigilados(QWidget):
    COL_TIENDA, COL_NOMBRE, COL_ID, COL_PESO, COL_UMBRAL, COL_FAVORITO, COL_ACTIVO = range(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_filtro = QComboBox()
        self.combo_filtro.addItem("Todas")
        self.combo_filtro.addItems(sorted(TIENDAS_CONOCIDAS))
        self.combo_filtro.currentTextChanged.connect(self._refrescar_tabla)

        boton_refrescar = QPushButton("Refrescar")
        boton_refrescar.clicked.connect(self._refrescar_tabla)
        boton_favorito = QPushButton("Alternar favorito")
        boton_favorito.clicked.connect(self._alternar_favorito)
        boton_quitar = QPushButton("Quitar (desactivar)")
        boton_quitar.clicked.connect(self._quitar)
        boton_borrar = QPushButton("Borrar definitivamente")
        boton_borrar.clicked.connect(self._borrar)

        fila_botones = QHBoxLayout()
        fila_botones.addWidget(self.combo_filtro)
        fila_botones.addWidget(boton_refrescar)
        fila_botones.addWidget(boton_favorito)
        fila_botones.addWidget(boton_quitar)
        fila_botones.addWidget(boton_borrar)

        self.tabla_productos = QTableWidget(0, 7)
        self.tabla_productos.setHorizontalHeaderLabels(
            ["Tienda", "Nombre", "ID", "Peso", "Umbral", "Favorito", "Activo"]
        )
        self.tabla_productos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_productos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_productos.itemSelectionChanged.connect(self._cargar_historial)

        self.tabla_historial = QTableWidget(0, 4)
        self.tabla_historial.setHorizontalHeaderLabels(["Fecha/Hora", "Estado", "Precio", "Moneda"])
        self.tabla_historial.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.addLayout(fila_botones)
        layout.addWidget(QLabel("Productos vigilados (peso y umbral son editables directo en la tabla):"))
        layout.addWidget(self.tabla_productos)
        layout.addWidget(QLabel("Historial del producto seleccionado:"))
        layout.addWidget(self.tabla_historial)

        self._claves_por_fila = []
        self._refrescar_tabla()

    # --- carga de la tabla ---

    def _refrescar_tabla(self):
        filtro = self.combo_filtro.currentText()
        productos = storage.cargar_watchlist()
        filas = [
            (clave, p) for clave, p in productos.items()
            if filtro == "Todas" or p.get("tienda") == filtro
        ]
        self.tabla_productos.setRowCount(len(filas))
        self._claves_por_fila = []
        for fila, (clave, p) in enumerate(filas):
            self._claves_por_fila.append(clave)
            self.tabla_productos.setItem(fila, self.COL_TIENDA, QTableWidgetItem(p.get("tienda", "")))
            self.tabla_productos.setItem(fila, self.COL_NOMBRE, QTableWidgetItem(p.get("nombre_producto", "")))
            self.tabla_productos.setItem(
                fila, self.COL_ID,
                QTableWidgetItem(p.get("id_producto_interno") or p.get("id_producto", "")),
            )
            self._colocar_spin_peso(fila, clave, p)
            self._colocar_campo_umbral(fila, clave, p)
            self.tabla_productos.setItem(
                fila, self.COL_FAVORITO, QTableWidgetItem("★" if p.get("favorito") else ""),
            )
            self.tabla_productos.setItem(
                fila, self.COL_ACTIVO, QTableWidgetItem("sí" if p.get("activado") else "no"),
            )
        self.tabla_historial.setRowCount(0)

    def _colocar_spin_peso(self, fila: int, clave: str, producto: dict):
        spin = QSpinBox()
        spin.setRange(0, 10)
        spin.setValue(int(producto.get("peso", 0)))
        spin.editingFinished.connect(lambda: self._guardar_peso(clave, spin))
        self.tabla_productos.setCellWidget(fila, self.COL_PESO, spin)

    def _colocar_campo_umbral(self, fila: int, clave: str, producto: dict):
        campo = QLineEdit()
        umbral = producto.get("umbral_aviso")
        campo.setText("" if umbral is None else str(umbral))
        campo.setPlaceholderText("sin umbral")
        campo.editingFinished.connect(lambda: self._guardar_umbral(clave, campo))
        self.tabla_productos.setCellWidget(fila, self.COL_UMBRAL, campo)

    # --- edición in-place ---

    def _guardar_peso(self, clave: str, spin: QSpinBox):
        nuevo_peso = spin.value()
        productos = storage.cargar_watchlist()
        producto = productos.get(clave)
        if producto is None or producto.get("peso") == nuevo_peso:
            return
        if nuevo_peso == 0:
            confirmacion = QMessageBox.question(
                self, "Confirmar",
                f"Peso 0 saca a '{producto.get('nombre_producto')}' de la cola automática. ¿Continuar?",
            )
            if confirmacion != QMessageBox.StandardButton.Yes:
                spin.setValue(producto.get("peso", 1))
                return
        error = storage.set_peso(clave, nuevo_peso)
        if error:
            QMessageBox.warning(self, "Error", error)
            spin.setValue(producto.get("peso", 1))

    def _guardar_umbral(self, clave: str, campo: QLineEdit):
        texto = campo.text().strip()
        valor = None if texto == "" else texto
        error = storage.set_umbral(clave, valor)
        if error:
            QMessageBox.warning(self, "Error", error)
            productos = storage.cargar_watchlist()
            producto = productos.get(clave, {})
            umbral_actual = producto.get("umbral_aviso")
            campo.setText("" if umbral_actual is None else str(umbral_actual))

    # --- historial ---

    def _fila_seleccionada(self):
        filas = self.tabla_productos.selectionModel().selectedRows()
        if not filas:
            return None
        indice = filas[0].row()
        if indice >= len(self._claves_por_fila):
            return None
        return self._claves_por_fila[indice]

    def _cargar_historial(self):
        clave = self._fila_seleccionada()
        self.tabla_historial.setRowCount(0)
        if clave is None:
            return
        historial = storage.cargar_historial().get(clave, {}).get("historial", [])
        self.tabla_historial.setRowCount(len(historial))
        for fila, registro in enumerate(historial):
            valores = [
                registro.get("fecha_hora", ""),
                registro.get("estado", ""),
                str(registro.get("precio", "")),
                registro.get("moneda", ""),
            ]
            for columna, texto in enumerate(valores):
                self.tabla_historial.setItem(fila, columna, QTableWidgetItem(texto))

    # --- acciones de fila ---

    def _alternar_favorito(self):
        clave = self._fila_seleccionada()
        if clave is None:
            return
        productos = storage.cargar_watchlist()
        producto = productos.get(clave)
        if producto is None:
            return
        error = storage.set_favorito(clave, not producto.get("favorito", False))
        if error:
            QMessageBox.warning(self, "Error", error)
        self._refrescar_tabla()

    def _quitar(self):
        clave = self._fila_seleccionada()
        if clave is None:
            return
        storage.set_activado(clave, False)
        self._refrescar_tabla()

    def _borrar(self):
        clave = self._fila_seleccionada()
        if clave is None:
            return
        confirmacion = QMessageBox.question(
            self, "Confirmar", "¿Borrar este producto y todo su historial? Es irreversible.",
        )
        if confirmacion == QMessageBox.StandardButton.Yes:
            storage.eliminar_producto(clave)
            self._refrescar_tabla()


class VentanaListas(QMainWindow):
    """Ventana independiente, para cuando este archivo se ejecuta solo."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("price_monitor — Vigilados")
        self.resize(900, 650)
        self.setCentralWidget(TabVigilados())
        try:
            with open(QSS_PATH, "r", encoding="utf-8") as archivo:
                self.setStyleSheet(archivo.read())
        except FileNotFoundError:
            pass


def iniciar_ventana_listas():
    from core import notifier
    app = notifier._get_app()
    ventana = VentanaListas()
    ventana.show()
    app.exec()


if __name__ == "__main__":
    iniciar_ventana_listas()
