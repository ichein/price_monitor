# visuals/configuracion.py
# Ventana/pestaña de configuración: Telegram, correo, popups y segundo plano.
# Puede abrirse sola (python visuals/configuracion.py) o incrustarse como
# pestaña dentro de visual_main.py.

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from core import notifier
from core.extras.recode import RAIZ_PROYECTO, RUTA_USER_DATA, guardar_config_directo, actualizar_seccion, _cargar_json

QSS_PATH = RAIZ_PROYECTO / "style" / "visual_main.qss"


def _leer_config_usuario() -> dict:
    try:
        return _cargar_json(RUTA_USER_DATA)
    except (FileNotFoundError, Exception):
        return {}


class TabConfiguracion(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(self._seccion_telegram())
        layout.addWidget(self._seccion_correo())
        layout.addWidget(self._seccion_popups())
        layout.addWidget(self._seccion_segundo_plano())
        layout.addStretch()

    def _config_actual(self) -> dict:
        return _leer_config_usuario()

    def _seccion_telegram(self) -> QGroupBox:
        caja = QGroupBox("Telegram")
        config = self._config_actual().get("telegram_config", {})
        self.campo_token = QLineEdit(str(config.get("token") or ""))
        self.campo_chat_id = QLineEdit(str(config.get("chat_id") or ""))
        boton = QPushButton("Guardar Telegram")
        boton.clicked.connect(self._guardar_telegram)
        form = QFormLayout()
        form.addRow("Token:", self.campo_token)
        form.addRow("Chat ID:", self.campo_chat_id)
        form.addRow(boton)
        caja.setLayout(form)
        return caja

    def _guardar_telegram(self):
        resultado = guardar_config_directo("telegram_config", {
            "token": self.campo_token.text().strip(),
            "chat_id": self.campo_chat_id.text().strip(),
        })
        self._avisar(resultado is not None, "Telegram guardado." if resultado else "Revisa los valores de Telegram.")

    def _seccion_correo(self) -> QGroupBox:
        caja = QGroupBox("Correo (Gmail)")
        config = self._config_actual().get("correo_config", {})
        self.campo_correo_remitente = QLineEdit(config.get("correo_remitente") or "")
        self.campo_correo_receptor = QLineEdit(config.get("correo_receptor") or "")
        self.campo_correo_clave = QLineEdit(config.get("contraseña") or "")
        self.campo_correo_clave.setEchoMode(QLineEdit.EchoMode.Password)
        boton = QPushButton("Guardar correo")
        boton.clicked.connect(self._guardar_correo)
        form = QFormLayout()
        form.addRow("Remitente:", self.campo_correo_remitente)
        form.addRow("Receptor:", self.campo_correo_receptor)
        form.addRow("Contraseña:", self.campo_correo_clave)
        form.addRow(boton)
        caja.setLayout(form)
        return caja

    def _guardar_correo(self):
        resultado = guardar_config_directo("correo_config", {
            "correo_remitente": self.campo_correo_remitente.text().strip(),
            "correo_receptor": self.campo_correo_receptor.text().strip(),
            "contraseña": self.campo_correo_clave.text(),
        })
        self._avisar(resultado is not None, "Correo guardado." if resultado else "Revisa los valores de correo.")

    def _seccion_popups(self) -> QGroupBox:
        caja = QGroupBox("Popups (apariencia)")
        config = self._config_actual().get("popup_config", {})
        self.check_popup_activado = QCheckBox("Popups activados")
        self.check_popup_activado.setChecked(bool(config.get("popup_activado", False)))
        self.spin_entrada = QSpinBox(); self.spin_entrada.setRange(0, 5000)
        self.spin_entrada.setValue(int(config.get("tiempo_entrada", 300)))
        self.spin_salida = QSpinBox(); self.spin_salida.setRange(0, 5000)
        self.spin_salida.setValue(int(config.get("tiempo_salida", 300)))
        self.spin_separacion = QSpinBox(); self.spin_separacion.setRange(0, 200)
        self.spin_separacion.setValue(int(config.get("separacion_popups", 8)))
        boton = QPushButton("Guardar apariencia de popups")
        boton.clicked.connect(self._guardar_popups)
        boton_probar = QPushButton("Probar popup")
        boton_probar.clicked.connect(self._probar_popup)
        form = QFormLayout()
        form.addRow(self.check_popup_activado)
        form.addRow("Tiempo entrada (ms):", self.spin_entrada)
        form.addRow("Tiempo salida (ms):", self.spin_salida)
        form.addRow("Separación entre popups (px):", self.spin_separacion)
        form.addRow(boton)
        form.addRow(boton_probar)
        caja.setLayout(form)
        return caja

    def _guardar_popups(self):
        ok = actualizar_seccion(RUTA_USER_DATA, "popup_config", {
            "popup_activado": self.check_popup_activado.isChecked(),
            "tiempo_entrada": self.spin_entrada.value(),
            "tiempo_salida": self.spin_salida.value(),
            "separacion_popups": self.spin_separacion.value(),
        })
        self._avisar(ok, "Configuración de popups guardada." if ok else "No se pudo guardar.")

    def _probar_popup(self):
        notifier.mostrar_popup(
            {"tipo": "info", "titulo": "Prueba", "mensaje": "Popup de prueba desde la GUI."},
            forzar=True,
        )

    def _seccion_segundo_plano(self) -> QGroupBox:
        caja = QGroupBox("Segundo plano")
        config = self._config_actual().get("segundo_plano_config", {})
        disparadores = config.get("disparadores", {})
        self.check_sp_activado = QCheckBox("Activado al iniciar el programa")
        self.check_sp_activado.setChecked(bool(config.get("activado", False)))
        self.check_sp_12h = QCheckBox("Disparador: cada 12h")
        self.check_sp_12h.setChecked(bool(disparadores.get("cada_12h", True)))
        self.check_sp_iniciar = QCheckBox("Disparador: al iniciar el programa")
        self.check_sp_iniciar.setChecked(bool(disparadores.get("al_iniciar_programa", False)))
        boton = QPushButton("Guardar segundo plano")
        boton.clicked.connect(self._guardar_segundo_plano)
        form = QFormLayout()
        form.addRow(self.check_sp_activado)
        form.addRow(self.check_sp_12h)
        form.addRow(self.check_sp_iniciar)
        form.addRow(QLabel("('al volver del reposo' y 'antes de apagar' aún no están implementados)"))
        form.addRow(boton)
        caja.setLayout(form)
        return caja

    def _guardar_segundo_plano(self):
        ok = actualizar_seccion(RUTA_USER_DATA, "segundo_plano_config", {
            "activado": self.check_sp_activado.isChecked(),
            "disparadores": {
                "cada_12h": self.check_sp_12h.isChecked(),
                "al_iniciar_programa": self.check_sp_iniciar.isChecked(),
                "al_volver_reposo": False,
                "antes_apagar": False,
            },
        })
        self._avisar(ok, "Configuración de segundo plano guardada." if ok else "No se pudo guardar.")

    def _avisar(self, ok: bool, texto: str):
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Icon.Information if ok else QMessageBox.Icon.Warning)
        caja.setText(texto)
        caja.exec()


class VentanaConfiguracion(QMainWindow):
    """Ventana independiente, para cuando este archivo se ejecuta solo."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("price_monitor — Configuración")
        self.resize(500, 650)
        self.setCentralWidget(TabConfiguracion())
        try:
            with open(QSS_PATH, "r", encoding="utf-8") as archivo:
                self.setStyleSheet(archivo.read())
        except FileNotFoundError:
            pass


def iniciar_ventana_configuracion():
    app = notifier._get_app()
    ventana = VentanaConfiguracion()
    ventana.show()
    app.exec()


if __name__ == "__main__":
    iniciar_ventana_configuracion()