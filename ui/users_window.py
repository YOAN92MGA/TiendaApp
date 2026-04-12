# ui/users_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDialog, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from services.user_service import (
    get_all_users, create_user, update_user_role, update_user_password, delete_user
)

class UsersWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.current_user = user  # usuario logueado
        self.setWindowTitle("Gestión de Usuarios")
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()

        # Botón para nuevo usuario
        self.new_btn = QPushButton("➕ Nuevo Usuario")
        self.new_btn.clicked.connect(self.create_user_dialog)
        layout.addWidget(self.new_btn)

        # Tabla de usuarios
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Usuario", "Rol", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_users()

    def load_users(self):
        users = get_all_users(self.db)
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(u.id)))
            self.table.setItem(row, 1, QTableWidgetItem(u.username))
            # Combo para rol
            role_combo = QComboBox()
            role_combo.addItems(["admin", "employee"])
            role_combo.setCurrentText(u.role)
            role_combo.currentIndexChanged.connect(lambda _, uid=u.id, cb=role_combo: self.change_role(uid, cb.currentText()))
            self.table.setCellWidget(row, 2, role_combo)
            # Botones de acciones
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            change_pw_btn = QPushButton("Cambiar contraseña")
            change_pw_btn.clicked.connect(lambda _, uid=u.id: self.change_password_dialog(uid))
            delete_btn = QPushButton("Eliminar")
            delete_btn.clicked.connect(lambda _, uid=u.id: self.delete_user(uid))
            btn_layout.addWidget(change_pw_btn)
            btn_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 3, btn_widget)

    def change_role(self, user_id, new_role):
        try:
            update_user_role(self.db, user_id, new_role)
            QMessageBox.information(self, "Rol actualizado", f"Rol cambiado a {new_role}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def change_password_dialog(self, user_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cambiar contraseña")
        layout = QFormLayout()
        new_pw = QLineEdit()
        new_pw.setEchoMode(QLineEdit.Password)
        confirm_pw = QLineEdit()
        confirm_pw.setEchoMode(QLineEdit.Password)
        layout.addRow("Nueva contraseña:", new_pw)
        layout.addRow("Confirmar:", confirm_pw)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            if new_pw.text() != confirm_pw.text():
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
                return
            if len(new_pw.text()) < 4:
                QMessageBox.warning(self, "Error", "La contraseña debe tener al menos 4 caracteres")
                return
            try:
                update_user_password(self.db, user_id, new_pw.text())
                QMessageBox.information(self, "Éxito", "Contraseña actualizada")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def create_user_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuevo Usuario")
        layout = QFormLayout()
        username = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.Password)
        confirm = QLineEdit()
        confirm.setEchoMode(QLineEdit.Password)
        role_combo = QComboBox()
        role_combo.addItems(["employee", "admin"])
        layout.addRow("Usuario:", username)
        layout.addRow("Contraseña:", password)
        layout.addRow("Confirmar:", confirm)
        layout.addRow("Rol:", role_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            if not username.text():
                QMessageBox.warning(self, "Error", "Nombre de usuario requerido")
                return
            if password.text() != confirm.text():
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
                return
            if len(password.text()) < 4:
                QMessageBox.warning(self, "Error", "Contraseña muy corta (mínimo 4 caracteres)")
                return
            try:
                create_user(self.db, username.text(), password.text(), role_combo.currentText())
                QMessageBox.information(self, "Éxito", "Usuario creado")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_user(self, user_id):
        # No permitir eliminar al propio usuario logueado
        if user_id == self.current_user.id:
            QMessageBox.warning(self, "Error", "No puede eliminar su propio usuario.")
            return
        reply = QMessageBox.question(self, "Confirmar", "¿Eliminar este usuario?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                delete_user(self.db, user_id)
                QMessageBox.information(self, "Éxito", "Usuario eliminado")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))