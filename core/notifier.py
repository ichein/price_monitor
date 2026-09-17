#Nota: Envía avisos por consola, Telegram, correo o ventana emergente.
import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QHBoxLayout, QVBoxLayout, QDialog, QLabel
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
    def centrar_en_padre(self, parent):
        geo_padre = parent.Geometry()
        x = geo_padre.x() + (geo_padre.width() - self.width()) // 2
        y = geo_padre.y() + (geo_padre.height() - self.height()) // 2
        self.move(x, y)
    #----------------------
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(mensaje["titulo"])
        self.setGeometry(100, 100, 100, 100)
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
        if parent:
            self.centrar_en_padre(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTitleHint
        )

app = QApplication(sys.argv)
with open("style/popup.qss", "r") as archivo:
    app.setStyleSheet(archivo.read())

#prueva de pop up
ventana = popup(self)
ventana.show()
sys.exit(app.exec())