# Nota: Envía avisos por consola, Telegram, correo o ventana emergente.
import sys
import json
import requests
from PyQt6.QtWidgets import QApplication, QPushButton, QHBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
try:
    from .extras.recode import y_or_n, modificar_json, limpiar_datos, input_con_timeout
except ImportError:
    from extras.recode import y_or_n, modificar_json, limpiar_datos, input_con_timeout

with open("data/user_data.json", "r") as archivo:
    config = json.load(archivo)


# config de la notificación por telegram

bot_token = config["telegram_config"].get("token")
chat_id = config["telegram_config"].get("chat_id")


# config de la notificación por correo
#       solo admite gmail
correo_config = config.setdefault("correo_config", {})
correo_receptor = correo_config.get("correo_receptor")
correo_remitente = correo_config.get("correo_remitente")
contraseña = correo_config.get("contraseña")

# Configuración de la ventana emergente
TIEMPO_ENTRADA = config["popup_config"]["tiempo_entrada"]
TIEMPO_SALIDA = config["popup_config"]["tiempo_salida"]
RADIO_SUPERIOR_IZQUIERDO = config["popup_config"]["radio_superior_izquierdo"]
RADIO_SUPERIOR_DERECHO = config["popup_config"]["radio_superior_derecho"]
RADIO_INFERIOR_IZQUIERDO = config["popup_config"]["radio_inferior_izquierdo"]
RADIO_INFERIOR_DERECHO = config["popup_config"]["radio_inferior_derecho"]
SEPARACION_POPUPS = config["popup_config"]["separacion_popups"]


def comprobar_datos_telegram():
    global bot_token, chat_id
    if bot_token in ("", None) or chat_id in ("", None):
        print("La configuración de Telegram no está completa")
        llaves_faltantes = [
            llave for llave, valor in (("token", bot_token), ("chat_id", chat_id))
            if valor in ("", None)
        ]
        valores_guardados = modificar_json("telegram_config", llaves_faltantes)
        if valores_guardados is None:
            return
        bot_token = valores_guardados.get("token", bot_token)
        chat_id = valores_guardados.get("chat_id", chat_id)


def comprobacion_datos_correo():
    global correo_receptor, correo_remitente, contraseña
    if (
        correo_receptor in ("", None) or correo_remitente in ("", None) or contraseña in ("", None)):
        print("La configuración de correo no está completa")
        llaves_faltantes = [
            llave for llave, valor in (
                ("correo_receptor", correo_receptor),
                ("correo_remitente", correo_remitente),
                ("contraseña", contraseña),
            )
            if valor in ("", None)
        ]
        valores_guardados = modificar_json("correo_config", llaves_faltantes)
        if valores_guardados is None:
            return
        correo_receptor = valores_guardados.get("correo_receptor", correo_receptor)
        correo_remitente = valores_guardados.get("correo_remitente", correo_remitente)
        contraseña = valores_guardados.get("contraseña", contraseña)


# mensaje de telegram

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


# correo de notificación

def enviar_correo(remitente, receptor, asunto, mensaje, contraseña):
    comprobacion_datos_correo()
    if not remitente or not receptor or not asunto or not mensaje or not contraseña:
        return
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = receptor
    msg['Subject'] = asunto
    msg.attach(MIMEText(mensaje, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, contraseña)
        server.sendmail(remitente, receptor, msg.as_string())
        server.quit()
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

# comando a copiar cuando se llama la función enviar_correo
# enviar_correo(correo_remitente, correo_receptor, mensaje["titulo"], mensaje["mensaje"], contraseña)


# pop up de notificación

class popup(QDialog):
    popups_activos = []
    popups_max = 10

    @classmethod
    def _reposicionar_pila(cls):
        if not cls.popups_activos:
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        base_x = geo.right() - 250 - 10
        base_y = geo.bottom() - 100 - 10
        for index, popup_widget in enumerate(cls.popups_activos):
            y = base_y - (index * SEPARACION_POPUPS)
            popup_widget.move(base_x, y)
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
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 10
            y = geo.bottom() - self.height() - 10 - ((len(self.popups_activos) - 1) * SEPARACION_POPUPS)
            self.anim_entrada = QPropertyAnimation(self, b"pos")
            self.anim_entrada.setDuration(TIEMPO_ENTRADA)
            self.anim_entrada.setStartValue(QPoint(geo.right(), y))
            self.anim_entrada.setEndValue(QPoint(x, y))
            self.anim_entrada.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim_entrada.start()
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
            self.anim_salida = QPropertyAnimation(self, b"pos")
            self.anim_salida.setDuration(TIEMPO_SALIDA)
            self.anim_salida.setStartValue(pos_actual)
            self.anim_salida.setEndValue(pos_final)
            self.anim_salida.setEasingCurve(QEasingCurve.Type.InCubic)
            self.anim_salida.finished.connect(self._finalizar_cierre)
            self.anim_salida.start()
        else:
            event.accept()

    def _finalizar_cierre(self):
        if self in self.popups_activos:
            self.popups_activos.remove(self)
            self.__class__._reposicionar_pila()
        self.close()


_app = None


def _get_app():
    #Crea (o reutiliza) el QApplication se ejecuta solo cuando se va a mostrar un popup
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication(sys.argv)
        with open("style/popup.qss", "r") as archivo:
            estilo = archivo.read()
        _app.setStyleSheet(
            estilo
            .replace("__RADIO_SUPERIOR_IZQUIERDO__", f"{RADIO_SUPERIOR_IZQUIERDO}px")
            .replace("__RADIO_SUPERIOR_DERECHO__", f"{RADIO_SUPERIOR_DERECHO}px")
            .replace("__RADIO_INFERIOR_IZQUIERDO__", f"{RADIO_INFERIOR_IZQUIERDO}px")
            .replace("__RADIO_INFERIOR_DERECHO__", f"{RADIO_INFERIOR_DERECHO}px")
        )
    return _app


def mostrar_popup(mensaje: dict):
    #Punto de entrada público para disparar un popup de notificación.
    #mensaje: {"tipo", "titulo", "mensaje"}
    app = _get_app()
    ventana = popup(mensaje)
    ventana.show()
    app.exec()


# Prueba rápida — no se ejecuta al importar el módulo
"""__name__ == "__main__":
    mostrar_popup({
        "tipo": "info",
        "titulo": "Aviso",
        "mensaje": "Este es un mensaje de prueba.",
    })"""