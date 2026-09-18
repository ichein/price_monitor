import sys
import json
import requests
from PyQt6.QtWidgets import QApplication, QPushButton, QHBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
try:
    from .extras.recode import modificar_json
except ImportError:
    from extras.recode import modificar_json
with open("data/user_data.json", "r") as archivo:
    config = json.load(archivo)
bot_token = config["telegram_config"].get("token")
chat_id = config["telegram_config"].get("chat_id")
correo_config = config.setdefault("correo_config", {})
correo_receptor = correo_config.get("correo_receptor")
correo_remitente = correo_config.get("correo_remitente")
contraseña = correo_config.get("contraseña")
popup_config = config["popup_config"]
TIEMPO_ENTRADA = popup_config["tiempo_entrada"]
TIEMPO_SALIDA = popup_config["tiempo_salida"]
RADIOS = {
    "__RADIO_SUPERIOR_IZQUIERDO__": popup_config["radio_superior_izquierdo"],
    "__RADIO_SUPERIOR_DERECHO__": popup_config["radio_superior_derecho"],
    "__RADIO_INFERIOR_IZQUIERDO__": popup_config["radio_inferior_izquierdo"],
    "__RADIO_INFERIOR_DERECHO__": popup_config["radio_inferior_derecho"],
}
SEPARACION_POPUPS = popup_config["separacion_popups"]
def _completar_configuracion(seccion, valores_actuales, mensaje):
    llaves_faltantes = [llave for llave, valor in valores_actuales.items() if valor in ("", None)]
    if not llaves_faltantes:
        return valores_actuales
    print(mensaje)
    valores_guardados = modificar_json(seccion, llaves_faltantes)
    if valores_guardados is None:
        return None
    return {llave: valores_guardados.get(llave, valor) for llave, valor in valores_actuales.items()}

def comprobar_datos_telegram():
    global bot_token, chat_id
    valores_actualizados = _completar_configuracion("telegram_config", {"token": bot_token, "chat_id": chat_id}, "La configuración de Telegram no está completa")
    if valores_actualizados is None:
        return
    bot_token = valores_actualizados["token"]
    chat_id = valores_actualizados["chat_id"]
def comprobacion_datos_correo():
    global correo_receptor, correo_remitente, contraseña
    valores_actualizados = _completar_configuracion("correo_config", {"correo_receptor": correo_receptor, "correo_remitente": correo_remitente, "contraseña": contraseña}, "La configuración de correo no está completa")
    if valores_actualizados is None:
        return
    correo_receptor = valores_actualizados["correo_receptor"]
    correo_remitente = valores_actualizados["correo_remitente"]
    contraseña = valores_actualizados["contraseña"]
def enviar_mensaje_telegram(mensaje: dict):
    comprobar_datos_telegram()
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{mensaje['titulo']} {mensaje['mensaje']}",
    }
    response = requests.post(url, data=payload)
    return response.status_code == 200
def enviar_correo(remitente, receptor, asunto, mensaje, contraseña_arg):
    comprobacion_datos_correo()
    remitente = remitente or correo_remitente
    receptor = receptor or correo_receptor
    clave = contraseña_arg or contraseña
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
def _animar(widget, inicio, fin, duracion, curva, al_terminar=None):
    animacion = QPropertyAnimation(widget, b"pos")
    animacion.setDuration(duracion)
    animacion.setStartValue(inicio)
    animacion.setEndValue(fin)
    animacion.setEasingCurve(curva)
    if al_terminar is not None:
        animacion.finished.connect(al_terminar)
    animacion.start()
    return animacion

class popup(QDialog):
    popups_activos = []
    popups_max = 10

    @classmethod
    def _posicion_pila(cls, indice, ancho, alto):
        screen = QApplication.primaryScreen()
        if screen is None:
            return None
        geo = screen.availableGeometry()
        x = geo.right() - ancho - 10
        y = geo.bottom() - alto - 10 - (indice * SEPARACION_POPUPS)
        return geo, QPoint(x, y)

    @classmethod
    def _reposicionar_pila(cls):
        if not cls.popups_activos:
            return
        for index, popup_widget in enumerate(cls.popups_activos):
            posicion = cls._posicion_pila(index, popup_widget.width(), popup_widget.height())
            if posicion is None:
                continue
            _, punto = posicion
            popup_widget.move(punto)
            popup_widget.raise_()
    def __init__(self, mensaje: dict):
        super().__init__()
        self.mensaje = mensaje
        self._cerrando = False
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
        label.setMinimumHeight(100)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        boton = QPushButton("X")
        boton.clicked.connect(self.close)
        boton.setMinimumHeight(100)
        main_layout.addWidget(label)
        main_layout.addWidget(boton)
        self.setLayout(main_layout)
        self.setFixedSize(250, 100)
        self.popups_activos.append(self)
        self._reposicionar_pila()
        posicion = self._posicion_pila(len(self.popups_activos) - 1, self.width(), self.height())
        if posicion is not None:
            geo, punto = posicion
            self.anim_entrada = _animar(
                self, QPoint(geo.right(), punto.y()), punto,
                TIEMPO_ENTRADA, QEasingCurve.Type.OutCubic,
            )
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.close)
        timer.start(10000)
    def closeEvent(self, event):
        if not self._cerrando:
            event.ignore()
            self._cerrando = True
            pos_actual = self.pos()
            screen = QApplication.primaryScreen()
            pos_final = QPoint(pos_actual.x(), pos_actual.y())
            if screen is not None:
                geo = screen.availableGeometry()
                pos_final = QPoint(geo.right(), pos_actual.y())
            self.anim_salida = _animar(
                self, pos_actual, pos_final,
                TIEMPO_SALIDA, QEasingCurve.Type.InCubic,
                self._finalizar_cierre,
            )
        else:
            event.accept()
    def _finalizar_cierre(self):
        if self in self.popups_activos:
            self.popups_activos.remove(self)
            self.__class__._reposicionar_pila()
        self.close()
_app = None
def _get_app():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication(sys.argv)
        with open("style/popup.qss", "r") as archivo:
            estilo = archivo.read()
        for marcador, radio in RADIOS.items():
            estilo = estilo.replace(marcador, f"{radio}px")
        _app.setStyleSheet(estilo)
    return _app
def mostrar_popup(mensaje: dict):
    app = _get_app()
    ventana = popup(mensaje)
    ventana.show()
    app.exec()