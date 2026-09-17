#Nota: Envía avisos por consola, Telegram, correo o ventana emergente.
import sys
from  PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle(mensaje["titulo"])
        self.setGeometry(100, 100, 100, 100)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(mensaje["mensaje"]))
        boton=QPushButton("X")
        boton.clicked.connect(self.close)
        boton.setGeometry(50, 50, 50, 30)
        layout.addWidget(boton)
        self.setLayout(layout)
        self.setFixedSize(250, 100)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTitleHint)

app = QApplication(sys.argv)
with open("../style/popup.qss", "r") as archivo:
    app.setStyleSheet(archivo.read())

#prueva de pop up
ventana = popup()
ventana.show()
sys.exit(app.exec())