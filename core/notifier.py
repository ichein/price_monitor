#Nota: Envía avisos por consola, Telegram, correo o ventana emergente.
import sys
import json
import shutil
import requests
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QPushButton, QHBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

with open("data/user_data.json", "r") as archivo:
    config = json.load(archivo)


#config de la notificación por telegram

bot_token = config["telegram_config"].get("token")
chat_id = config["telegram_config"].get("chat_id")


#config de la notificación por correo
#       solo admite gmail
correo_config = config.setdefault("correo_config", {})
correo_receptor = correo_config.get("correo_receptor")
correo_remitente = correo_config.get("correo_remitente")
contraseña = correo_config.get("contraseña")

#Configuración de la ventana emergente
TIEMPO_ENTRADA = config["popup_config"]["tiempo_entrada"]
TIEMPO_SALIDA = config["popup_config"]["tiempo_salida"]
RADIO_SUPERIOR_IZQUIERDO = config["popup_config"]["radio_superior_izquierdo"]
RADIO_SUPERIOR_DERECHO = config["popup_config"]["radio_superior_derecho"]
RADIO_INFERIOR_IZQUIERDO = config["popup_config"]["radio_inferior_izquierdo"]
RADIO_INFERIOR_DERECHO = config["popup_config"]["radio_inferior_derecho"]
SEPARACION_POPUPS = config["popup_config"]["separacion_popups"]

mensaje = {
    "tipo": "info",
    "titulo": "Aviso",
    "mensaje": "Este es un mensaje de prueba."
}

def comprobar_datos_telegram():
    global bot_token, chat_id
    if bot_token in ("", None) or chat_id in ("", None):
        print("La configuración de Telegram no está completa")
        if bot_token in ("", None):
            print("El token del bot no está configurado")
            bot_token = input("token del bot: ")
        if chat_id in ("", None):
            print("El ID del chat no está configurado")
            chat_id = input("ID del chat: ")
        config["telegram_config"].update({
            "token": bot_token,
            "chat_id": chat_id,
        })
        with open("data/user_data.json", "w") as archivo:
            json.dump(config, archivo, indent=4, ensure_ascii=False)

def comprobacion_datos_correo():
    global correo_receptor, correo_remitente, contraseña
    if (
        correo_receptor in ("", None) or correo_remitente in ("", None) or contraseña in ("", None)):
        print("La configuración de correo no está completa")
        if correo_receptor in ("", None):
            print("El correo receptor no está configurado")
            correo_receptor = input("correo receptor: ")
        if correo_remitente in ("", None):
            print("El correo remitente no está configurado")
            correo_remitente = input("correo remitente: ")
        if contraseña in ("", None):
            print("La contraseña no está configurada")
            contraseña = input("contraseña: ")
        config["correo_config"].update({
            "correo_receptor": correo_receptor,
            "correo_remitente": correo_remitente,
            "contraseña": contraseña,
        })
        with open("data/user_data.json", "w") as archivo:
            json.dump(config, archivo, indent=4, ensure_ascii=False)

#mensaje de telegram

def enviar_mensaje_telegram(mensaje):
    comprobar_datos_telegram()
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": [mensaje["titulo"] + " " + mensaje["mensaje"]]
    }
    response = requests.post(url, data=payload)
    return response.status_code == 200

#correo de notificación

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
#enviar_correo(correo_remitente, correo_receptor, mensaje["titulo"], mensaje["mensaje"], contraseña)

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
    def __init__(self):
        super().__init__()
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


app = QApplication(sys.argv)
with open("style/popup.qss", "r") as archivo:
    estilo = archivo.read()

app.setStyleSheet(
    estilo
    .replace("__RADIO_SUPERIOR_IZQUIERDO__", f"{RADIO_SUPERIOR_IZQUIERDO}px")
    .replace("__RADIO_SUPERIOR_DERECHO__", f"{RADIO_SUPERIOR_DERECHO}px")
    .replace("__RADIO_INFERIOR_IZQUIERDO__", f"{RADIO_INFERIOR_IZQUIERDO}px")
    .replace("__RADIO_INFERIOR_DERECHO__", f"{RADIO_INFERIOR_DERECHO}px")
)

def limpiar_datos():
    confirmar = input("¿Deseas limpiar todos los datos? (Y/N): ").strip().lower()
    if confirmar not in ("y", "yes"):
        print("Limpieza cancelada.")
        return
    config["telegram_config"] = {
        "telegram_activado": False,
        "token": None,
        "chat_id": None,
    }
    config["correo_config"] = {
        "correo_activado": False,
        "correo_remitente": None,
        "correo_receptor": None,
        "contraseña": None,
    }
    config.setdefault("popup_config", {})["popup_activado"] = False
    with open("data/user_data.json", "w", encoding="utf-8") as archivo:
        json.dump(config, archivo, indent=4, ensure_ascii=False)
    directorio_proyecto = Path(__file__).resolve().parent.parent
    for directorio_cache in directorio_proyecto.rglob("__pycache__"):
        if directorio_cache.is_dir():
            shutil.rmtree(directorio_cache)
    print("Datos y cache de Python limpiados correctamente.")
