from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox
)
from ui.dashboard import Dashboard

from sqlalchemy.orm import Session

from services.auth_service import authenticate_user


class LoginWindow(QWidget):

    def __init__(self, db: Session):

        super().__init__()

        self.db = db

        self.setWindowTitle("Sistema de Tienda")

        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.label = QLabel("Login")

        self.username = QLineEdit()

        self.username.setPlaceholderText("Usuario")

        self.password = QLineEdit()

        self.password.setPlaceholderText("Password")

        self.password.setEchoMode(QLineEdit.Password)

        self.button = QPushButton("Entrar")

        self.button.clicked.connect(self.login)

        layout.addWidget(self.label)

        layout.addWidget(self.username)

        layout.addWidget(self.password)

        layout.addWidget(self.button)

        self.setLayout(layout)

    def login(self):
        username = self.username.text()
        
        password = self.password.text()

        user = authenticate_user(self.db, username, password)

        if user:

            self.dashboard = Dashboard(self.db, user)  # pasamos también el usuario para roles futuros

            self.dashboard.show()

            self.close()

        else:

            QMessageBox.warning(self, "Error", "Credenciales incorrectas")