# Avisos por Telegram, correo y popups.
import json
import smtplib
import sys
import threading
from collections import deque
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests
from PyQt6.QtCore import (
    QEasingCurve, QEventLoop, QObject, QPoint, QPropertyAnimation, Qt, QThread,
    QTimer, pyqtSignal, pyqtSlot,
)
from PyQt6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton

from core.extras.recode import (
    RAIZ_PROYECTO, RUTA_USER_DATA, convertir_valor_config, modificar_json,
    valor_config_valido,
)

# Ruta del estilo del popup.
RUTA_ESTILO_POPUP = RAIZ_PROYECTO / "style" / "popup.qss"

# Configuración.
_config_cancelada = set()


def _leer_config() -> dict:
    try:
        with open(RUTA_USER_DATA, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
    except FileNotFoundError:
        print(f"[notifier] no existe {RUTA_USER_DATA}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[notifier] user_data.json no es un JSON válido: {e}")
        return {}
    return config if isinstance(config, dict) else {}


def _canal_activo(seccion: str, bandera: str) -> bool:
    """Comprueba si el canal está activado."""
    return bool((_leer_config().get(seccion) or {}).get(bandera, False))


def _completar_configuracion(seccion: str, llaves, mensaje: str) -> Optional[dict]:
    """Completa la configuración faltante."""
    datos = _leer_config().get(seccion) or {}
    faltantes = [k for k in llaves if not valor_config_valido(k, datos.get(k))]
    if not faltantes:
        return {k: convertir_valor_config(k, datos[k]) for k in llaves}
    if seccion in _config_cancelada:
        return None
    print(mensaje)
    guardados = modificar_json(seccion, faltantes)
    if guardados is None:
        _config_cancelada.add(seccion)
        return None
    return {
        k: guardados[k] if k in guardados else convertir_valor_config(k, datos[k])
        for k in llaves
    }


def comprobar_datos_telegram() -> Optional[dict]:
    return _completar_configuracion(
        "telegram_config", ("token", "chat_id"),
        "La configuración de Telegram no está completa",
    )


def comprobacion_datos_correo() -> Optional[dict]:
    return _completar_configuracion(
        "correo_config", ("correo_receptor", "correo_remitente", "contraseña"),
        "La configuración de correo no está completa",
    )

# Telegram y correo
def enviar_mensaje_telegram(mensaje: dict) -> bool:
    if not _canal_activo("telegram_config", "telegram_activado"):
        return False
    datos = comprobar_datos_telegram()
    if datos is None:
        return False
    url = f"https://api.telegram.org/bot{datos['token']}/sendMessage"
    payload = {
        "chat_id": datos["chat_id"],
        "text": f"{mensaje['titulo']} {mensaje['mensaje']}",
    }
    response = requests.post(url, data=payload)
    return response.status_code == 200


def enviar_correo(remitente, receptor, asunto, mensaje, contraseña_arg):
    if not _canal_activo("correo_config", "correo_activado"):
        return
    datos = comprobacion_datos_correo() or {}
    remitente = remitente or datos.get("correo_remitente")
    receptor = receptor or datos.get("correo_receptor")
    clave = contraseña_arg or datos.get("contraseña")
    if not remitente or not receptor or not asunto or not mensaje or not clave:
        return
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = receptor
    msg['Subject'] = asunto
    msg.attach(MIMEText(mensaje, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave)
        server.sendmail(remitente, receptor, msg.as_string())
        server.quit()
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

# Popups
ANCHO_POPUP = 250
ALTO_POPUP = 100
MARGEN_PANTALLA = 10
DURACION_POPUP_MS = 10000
DURACION_REACOMODO_MS = 150

POPUP_DEFAULTS = {
    "tiempo_entrada": 300,
    "tiempo_salida": 300,
    "radio_superior_izquierdo": 10,
    "radio_superior_derecho": 0,
    "radio_inferior_izquierdo": 10,
    "radio_inferior_derecho": 0,
    "separacion_popups": 8,
}

MARCADORES_RADIO = {
    "__RADIO_SUPERIOR_IZQUIERDO__": "radio_superior_izquierdo",
    "__RADIO_SUPERIOR_DERECHO__": "radio_superior_derecho",
    "__RADIO_INFERIOR_IZQUIERDO__": "radio_inferior_izquierdo",
    "__RADIO_INFERIOR_DERECHO__": "radio_inferior_derecho",
}

_AJUSTES = dict(POPUP_DEFAULTS)


def _entero(valor, defecto: int) -> int:
    try:
        return max(0, int(valor))
    except (TypeError, ValueError):
        return defecto


def _actualizar_ajustes(popup_config: dict) -> None:
    for llave, defecto in POPUP_DEFAULTS.items():
        _AJUSTES[llave] = _entero(popup_config.get(llave), defecto)


class _Senales(QObject):
    """Puente entre hilos."""
    solicitud = pyqtSignal(object)
    vacio = pyqtSignal()  # ya no queda ningún popup visible ni pendiente

    def __init__(self):
        super().__init__()
        self.solicitud.connect(self._atender)

    @pyqtSlot(object)
    def _atender(self, mensaje):
        popup.solicitar(mensaje)


class popup(QDialog):
    popups_activos = []
    popups_pendientes = deque()
    popups_max = 10

    # Pila
    @classmethod
    def _paso(cls) -> int:
        return ALTO_POPUP + _AJUSTES["separacion_popups"]

    @classmethod
    def _capacidad(cls) -> int:
        """Máximo de popups visibles."""
        maximo = max(1, cls.popups_max)
        screen = QApplication.primaryScreen()
        if screen is None:
            return maximo
        alto_util = screen.availableGeometry().height() - 2 * MARGEN_PANTALLA
        por_pantalla = max(1, (alto_util + _AJUSTES["separacion_popups"]) // cls._paso())
        return min(maximo, por_pantalla)

    @classmethod
    def _posicion_pila(cls, indice: int):
        screen = QApplication.primaryScreen()
        if screen is None:
            return None
        geo = screen.availableGeometry()
        x = geo.right() - ANCHO_POPUP - MARGEN_PANTALLA
        y = geo.bottom() - ALTO_POPUP - MARGEN_PANTALLA - indice * cls._paso()
        return geo, QPoint(x, y)

    @classmethod
    def _reacomodar_pila(cls):
        """Reacomoda la pila."""
        for indice, ventana in enumerate(cls.popups_activos):
            if ventana._cerrando:
                continue
            posicion = cls._posicion_pila(indice)
            if posicion is None:
                continue
            _, punto = posicion
            if ventana._destino == punto:
                continue
            ventana._mover_a(punto, DURACION_REACOMODO_MS, QEasingCurve.Type.OutCubic)

    @classmethod
    def _liberar_pendientes(cls):
        while cls.popups_pendientes and len(cls.popups_activos) < cls._capacidad():
            cls(cls.popups_pendientes.popleft())._entrar()
        if not cls.popups_activos and not cls.popups_pendientes and _senales is not None:
            _senales.vacio.emit()

    @classmethod
    def solicitar(cls, mensaje: dict):
        """Muestra el popup o lo encola."""
        if len(cls.popups_activos) >= cls._capacidad():
            cls.popups_pendientes.append(mensaje)
            return
        cls(mensaje)._entrar()

    # Ventana
    def __init__(self, mensaje: dict):
        super().__init__()
        self.mensaje = mensaje
        self._cerrando = False
        self._terminado = False
        self._anim = None
        self._destino = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(mensaje["titulo"])
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(mensaje["mensaje"])
        label.setWordWrap(True)
        label.setToolTip(mensaje["mensaje"])
        label.setMinimumHeight(100)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        boton = QPushButton("X")
        boton.clicked.connect(self.close)
        boton.setMinimumHeight(100)
        main_layout.addWidget(label)
        main_layout.addWidget(boton)
        self.setFixedSize(ANCHO_POPUP, ALTO_POPUP)
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.timeout.connect(self.close)

    def _mover_a(self, destino: QPoint, duracion: int, curva, al_terminar=None):
        """Mueve la ventana con animación."""
        if self._anim is not None:
            self._anim.stop()
            self._anim.deleteLater()
        self._destino = destino
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(duracion)
        anim.setStartValue(self.pos())
        anim.setEndValue(destino)
        anim.setEasingCurve(curva)
        if al_terminar is not None:
            anim.finished.connect(al_terminar)
        self._anim = anim
        anim.start()

    def _entrar(self):
        indice = len(self.popups_activos)
        self.popups_activos.append(self)
        posicion = self._posicion_pila(indice)
        if posicion is None:
            self.show()
        else:
            geo, punto = posicion
            self.move(QPoint(geo.right(), punto.y()))  # arranca fuera, en el borde derecho
            self.show()
            self._mover_a(punto, _AJUSTES["tiempo_entrada"], QEasingCurve.Type.OutCubic)
        self._temporizador.start(DURACION_POPUP_MS)

    # Cierre
    def reject(self):
        self.close()

    def closeEvent(self, event):
        if self._terminado:
            event.accept()
            return
        event.ignore()
        self._iniciar_salida()

    def _iniciar_salida(self):
        if self._cerrando:
            return
        self._cerrando = True
        self._temporizador.stop()
        screen = QApplication.primaryScreen()
        if screen is None:
            self._finalizar_cierre()
            return
        fuera = QPoint(screen.availableGeometry().right(), self.y())
        self._mover_a(fuera, _AJUSTES["tiempo_salida"], QEasingCurve.Type.InCubic,
                      self._finalizar_cierre)

    def _finalizar_cierre(self):
        self._terminado = True
        if self in self.popups_activos:
            self.popups_activos.remove(self)
        self.close()  # closeEvent lo acepta; WA_DeleteOnClose libera la ventana
        popup._reacomodar_pila()
        popup._liberar_pendientes()

# Qt app
_app = None
_senales = None
_bucle_persistente = False


def _get_app():
    global _app, _senales
    if _app is None:
        instancia = QApplication.instance()
        if instancia is None:
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError(
                    "Los popups necesitan que QApplication se cree en el hilo principal."
                )
            instancia = QApplication(sys.argv)
            instancia.setQuitOnLastWindowClosed(False)
        _app = instancia
        try:
            with open(RUTA_ESTILO_POPUP, "r", encoding="utf-8") as archivo:
                estilo = archivo.read()
            for marcador, llave in MARCADORES_RADIO.items():
                estilo = estilo.replace(marcador, f"{_AJUSTES[llave]}px")
            _app.setStyleSheet(estilo)
        except FileNotFoundError:
            print(f"[notifier] no se encontró {RUTA_ESTILO_POPUP}; los popups usarán el estilo por defecto")
    if _senales is None:
        _senales = _Senales()
        _senales.moveToThread(_app.thread())
    return _app


def _hay_bucle_activo() -> bool:
    if _bucle_persistente:
        return True
    try:
        return QThread.currentThread().loopLevel() > 0
    except AttributeError:
        return False


def _esperar_a_que_cierren():
    """Espera a que cierren los popups."""
    bucle = QEventLoop()
    _senales.vacio.connect(bucle.quit)
    try:
        bucle.exec()
    finally:
        _senales.vacio.disconnect(bucle.quit)


def iniciar_bucle_popups() -> int:
    """Inicia el bucle Qt principal."""
    global _bucle_persistente
    app = _get_app()
    _bucle_persistente = True
    try:
        return app.exec()
    finally:
        _bucle_persistente = False


def detener_bucle_popups():
    if _app is not None:
        _app.quit()


def mostrar_popups(mensajes: list, esperar: bool = True):
    """Muestra varios popups apilados."""
    config = _leer_config().get("popup_config") or {}
    if not config.get("popup_activado", False):
        return
    _actualizar_ajustes(config)
    _get_app()
    if threading.current_thread() is not threading.main_thread():
        for mensaje in mensajes:
            _senales.solicitud.emit(mensaje)
        return
    for mensaje in mensajes:
        popup.solicitar(mensaje)
    if esperar and popup.popups_activos and not _hay_bucle_activo():
        _esperar_a_que_cierren()


def mostrar_popup(mensaje: dict, esperar: bool = True):
    mostrar_popups([mensaje], esperar=esperar)