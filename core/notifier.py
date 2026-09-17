#Nota: Envía avisos por consola, Telegram, correo o ventana emergente.
import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QHBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint

TIEMPO_ENTRADA = 300
TIEMPO_SALIDA = 300
RADIO_SUPERIOR_IZQUIERDO = 10
RADIO_SUPERIOR_DERECHO = 0
RADIO_INFERIOR_IZQUIERDO = 10
RADIO_INFERIOR_DERECHO = 0
SEPARACION_POPUPS = 99

mensaje = {
    "tipo": "info",
    "titulo": "Aviso",
    "mensaje": "Este es un mensaje de prueba."
}

email_config = {
    "receptor": "user@example.com",
    "origen": None
}

telegram_config = {
    "token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID"
}


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

# prueba de 5 popups con 1 segundo entre cada uno
#for i in range(5):
#    QTimer.singleShot(i * 1000, lambda index=i: popup().show())
#sys.exit(app.exec())
