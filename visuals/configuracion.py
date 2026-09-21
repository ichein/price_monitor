# visuals/configuracion.py
# Telegram, correo, popups (con deslizadores + vista previa), segundo
# plano (con control inmediato), y apariencia (modo claro/oscuro).

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from core import notifier
from core.extras.recode import RUTA_USER_DATA, guardar_config_directo, actualizar_seccion, _cargar_json
from core.extras.tema import (
    PALETAS, RANGOS_DESLIZABLES, generar_qss_main, aplicar_modo,
    modo_actual, registrar_ventana, crear_boton,
)

import main as consola  # para iniciar/detener segundo plano en vivo


def _leer_config_usuario() -> dict:
    try:
        return _cargar_json(RUTA_USER_DATA)
    except Exception:
        return {}


class TabConfiguracion(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        contenido = QWidget()
        contenido_layout = QVBoxLayout(contenido)
        contenido_layout.addWidget(self._seccion_apariencia())
        contenido_layout.addWidget(self._seccion_telegram())
        contenido_layout.addWidget(self._seccion_correo())
        contenido_layout.addWidget(self._seccion_popups())
        contenido_layout.addWidget(self._seccion_segundo_plano())
        contenido_layout.addStretch()

        desplazamiento = QScrollArea()
        desplazamiento.setWidgetResizable(True)
        desplazamiento.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        desplazamiento.setWidget(contenido)

        layout = QVBoxLayout(self)
        layout.addWidget(desplazamiento)

    def _config_actual(self) -> dict:
        return _leer_config_usuario()

    # --- apariencia (modo claro/oscuro) ---

    def _seccion_apariencia(self) -> QGroupBox:
        caja = QGroupBox("Apariencia")
        self.check_modo_oscuro = QCheckBox("Modo oscuro")
        self.check_modo_oscuro.setChecked(modo_actual() == "oscuro")
        self.check_modo_oscuro.toggled.connect(self._cambiar_modo)
        form = QFormLayout()
        form.addRow(self.check_modo_oscuro)
        caja.setLayout(form)
        return caja

    def _cambiar_modo(self, activado: bool):
        aplicar_modo("oscuro" if activado else "claro")

    # --- telegram ---

    def _seccion_telegram(self) -> QGroupBox:
        caja = QGroupBox("Telegram")
        config = self._config_actual().get("telegram_config", {})
        self.campo_token = QLineEdit(str(config.get("token") or ""))
        self.campo_chat_id = QLineEdit(str(config.get("chat_id") or ""))
        boton = crear_boton("Guardar Telegram", self._guardar_telegram)
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

    # --- correo ---

    def _seccion_correo(self) -> QGroupBox:
        caja = QGroupBox("Correo (Gmail)")
        config = self._config_actual().get("correo_config", {})
        self.campo_correo_remitente = QLineEdit(config.get("correo_remitente") or "")
        self.campo_correo_receptor = QLineEdit(config.get("correo_receptor") or "")
        self.campo_correo_clave = QLineEdit(config.get("contraseña") or "")
        self.campo_correo_clave.setEchoMode(QLineEdit.EchoMode.Password)
        boton = crear_boton("Guardar correo", self._guardar_correo)
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

    # --- popups (deslizadores + vista previa) ---

    def _fila_deslizador(self, etiqueta_texto: str, llave: str, valor_inicial: int):
        minimo, maximo = RANGOS_DESLIZABLES[llave]
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimo, maximo)
        slider.setValue(int(valor_inicial))
        valor_label = QLabel(str(valor_inicial))
        valor_label.setFixedWidth(40)
        slider.valueChanged.connect(lambda v: valor_label.setText(str(v)))
        fila = QHBoxLayout()
        fila.addWidget(QLabel(etiqueta_texto))
        fila.addWidget(slider)
        fila.addWidget(valor_label)
        return fila, slider

    def _seccion_popups(self) -> QGroupBox:
        caja = QGroupBox("Popups")
        config = self._config_actual().get("popup_config", {})
        self.check_popup_activado = QCheckBox("Popups activados")
        self.check_popup_activado.setChecked(bool(config.get("popup_activado", False)))

        fila_entrada, self.slider_entrada = self._fila_deslizador(
            "Tiempo entrada (ms):", "tiempo_entrada", config.get("tiempo_entrada", 300))
        fila_salida, self.slider_salida = self._fila_deslizador(
            "Tiempo salida (ms):", "tiempo_salida", config.get("tiempo_salida", 300))
        fila_separacion, self.slider_separacion = self._fila_deslizador(
            "Separación entre popups (px):", "separacion_popups", config.get("separacion_popups", 8))
        fila_rsi, self.slider_rsi = self._fila_deslizador(
            "Radio superior izq.:", "radio_superior_izquierdo", config.get("radio_superior_izquierdo", 10))
        fila_rsd, self.slider_rsd = self._fila_deslizador(
            "Radio superior der.:", "radio_superior_derecho", config.get("radio_superior_derecho", 0))
        fila_rii, self.slider_rii = self._fila_deslizador(
            "Radio inferior izq.:", "radio_inferior_izquierdo", config.get("radio_inferior_izquierdo", 10))
        fila_rid, self.slider_rid = self._fila_deslizador(
            "Radio inferior der.:", "radio_inferior_derecho", config.get("radio_inferior_derecho", 0))

        boton_guardar = crear_boton("Guardar popups", self._guardar_popups)
        boton_previa = crear_boton("Vista previa", self._vista_previa_popup)

        layout = QVBoxLayout()
        layout.addWidget(self.check_popup_activado)
        for fila in (fila_entrada, fila_salida, fila_separacion, fila_rsi, fila_rsd, fila_rii, fila_rid):
            layout.addLayout(fila)
        fila_botones = QHBoxLayout()
        fila_botones.addWidget(boton_guardar)
        fila_botones.addWidget(boton_previa)
        layout.addLayout(fila_botones)
        caja.setLayout(layout)
        return caja

    def _valores_popup_actuales(self) -> dict:
        return {
            "tiempo_entrada": self.slider_entrada.value(),
            "tiempo_salida": self.slider_salida.value(),
            "separacion_popups": self.slider_separacion.value(),
            "radio_superior_izquierdo": self.slider_rsi.value(),
            "radio_superior_derecho": self.slider_rsd.value(),
            "radio_inferior_izquierdo": self.slider_rii.value(),
            "radio_inferior_derecho": self.slider_rid.value(),
        }

    def _guardar_popups(self):
        valores = self._valores_popup_actuales()
        valores["popup_activado"] = self.check_popup_activado.isChecked()
        ok = actualizar_seccion(RUTA_USER_DATA, "popup_config", valores)
        self._avisar(ok, "Configuración de popups guardada." if ok else "No se pudo guardar.")

    def _vista_previa_popup(self):
        modo = "oscuro" if self.check_modo_oscuro.isChecked() else "claro"
        notifier.previsualizar_popup(self._valores_popup_actuales(), modo, esperar=False)

    # --- segundo plano ---

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

        boton_guardar = crear_boton("Guardar segundo plano", self._guardar_segundo_plano)
        boton_iniciar = crear_boton("Iniciar ahora", self._iniciar_segundo_plano)
        boton_detener = crear_boton("Detener ahora", self._detener_segundo_plano)

        form = QFormLayout()
        form.addRow(self.check_sp_activado)
        form.addRow(self.check_sp_12h)
        form.addRow(self.check_sp_iniciar)
        form.addRow(QLabel("('al volver del reposo' y 'antes de apagar' aún no están implementados)"))
        form.addRow(boton_guardar)
        fila_control = QHBoxLayout()
        fila_control.addWidget(boton_iniciar)
        fila_control.addWidget(boton_detener)
        form.addRow(fila_control)
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

    def _iniciar_segundo_plano(self):
        scrapers = consola._cargar_scrapers()
        consola.iniciar_segundo_plano(scrapers)

    def _detener_segundo_plano(self):
        consola.detener_segundo_plano()

    # --- utilidad ---

    def _avisar(self, ok: bool, texto: str):
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Icon.Information if ok else QMessageBox.Icon.Warning)
        caja.setText(texto)
        caja.exec()


class VentanaConfiguracion(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("price_monitor — Configuración")
        self.resize(520, 750)
        self.setCentralWidget(TabConfiguracion())
        self.setStyleSheet(generar_qss_main())
        registrar_ventana(self)


def iniciar_ventana_configuracion():
    app = notifier._get_app()
    ventana = VentanaConfiguracion()
    ventana.show()
    app.exec()


if __name__ == "__main__":
    iniciar_ventana_configuracion()