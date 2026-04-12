# ui/backup_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from services.backup_service import create_backup, list_backups, restore_backup
import os

class BackupWindow(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Copias de Seguridad")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()

        # Botón para crear backup
        self.backup_btn = QPushButton("📀 Crear copia de seguridad")
        self.backup_btn.clicked.connect(self.do_backup)
        layout.addWidget(self.backup_btn)

        # Lista de backups existentes
        layout.addWidget(QLabel("Copias disponibles:"))
        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list)

        # Botones para restaurar y eliminar
        btn_layout = QHBoxLayout()
        self.restore_btn = QPushButton("🔄 Restaurar seleccionada")
        self.restore_btn.clicked.connect(self.do_restore)
        self.delete_btn = QPushButton("🗑 Eliminar seleccionada")
        self.delete_btn.clicked.connect(self.delete_backup)
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_backup_list()

    def refresh_backup_list(self):
        self.backup_list.clear()
        backups = list_backups()
        for b in backups:
            self.backup_list.addItem(b)

    def do_backup(self):
        try:
            backup_path = create_backup()
            QMessageBox.information(self, "Copia creada", f"Backup guardado en:\n{backup_path}")
            self.refresh_backup_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear backup:\n{str(e)}")

    def do_restore(self):
        selected = self.backup_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Selección", "Seleccione una copia de seguridad.")
            return
        backup_name = selected.text()
        reply = QMessageBox.question(self, "Restaurar", 
                                     f"¿Restaurar la copia '{backup_name}'?\nSe perderán los cambios no respaldados.\nLa aplicación se cerrará después de la restauración.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            restore_backup(backup_name)
            QMessageBox.information(self, "Restauración exitosa", "Base de datos restaurada. La aplicación se cerrará.")
            # Forzar salida de la aplicación
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al restaurar:\n{str(e)}")

    def delete_backup(self):
        selected = self.backup_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Selección", "Seleccione una copia para eliminar.")
            return
        backup_name = selected.text()
        reply = QMessageBox.question(self, "Eliminar", f"¿Eliminar la copia '{backup_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(os.path.join("backups", backup_name))
                self.refresh_backup_list()
                QMessageBox.information(self, "Eliminado", "Copia eliminada.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))