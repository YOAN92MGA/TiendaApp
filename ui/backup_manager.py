# ui/backup_manager.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLabel, QCheckBox
)
from PySide6.QtCore import QTimer, Qt
from services.backup_service import create_backup, list_backups, restore_backup
import os

class BackupManager(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Gestión de Respaldos")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()

        # Botón respaldo manual
        self.backup_btn = QPushButton("💾 Realizar respaldo manual")
        self.backup_btn.clicked.connect(self.do_backup)
        layout.addWidget(self.backup_btn)

        # Opción de respaldo automático (opcional)
        auto_layout = QHBoxLayout()
        self.auto_check = QCheckBox("Activar respaldo automático diario")
        self.auto_check.stateChanged.connect(self.toggle_auto_backup)
        auto_layout.addWidget(self.auto_check)
        auto_layout.addStretch()
        layout.addLayout(auto_layout)

        # Lista de respaldos existentes
        layout.addWidget(QLabel("Respaldos disponibles:"))
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(3)
        self.backup_table.setHorizontalHeaderLabels(["Archivo", "Fecha", "Tamaño (KB)"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backup_table.doubleClicked.connect(self.restore_selected)
        layout.addWidget(self.backup_table)

        self.refresh_btn = QPushButton("🔄 Refrescar lista")
        self.refresh_btn.clicked.connect(self.load_backups)
        layout.addWidget(self.refresh_btn)

        self.setLayout(layout)
        self.load_backups()

        self.timer = QTimer()
        self.timer.timeout.connect(self.do_auto_backup)
        self.auto_backup_enabled = False

    def do_backup(self):
        try:
            path = create_backup()  # usa tu función
            QMessageBox.information(self, "Respaldo exitoso", f"Respaldo guardado en:\n{path}")
            self.load_backups()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear el respaldo: {str(e)}")

    def do_auto_backup(self):
        if self.auto_backup_enabled:
            try:
                create_backup()
            except Exception as e:
                print(f"Error en respaldo automático: {e}")

    def toggle_auto_backup(self, state):
        self.auto_backup_enabled = (state == Qt.Checked)
        if self.auto_backup_enabled:
            self.timer.start(86400000)  # 24 horas
            QMessageBox.information(self, "Respaldo automático", "Se realizará un respaldo cada 24 horas.")
        else:
            self.timer.stop()

    def load_backups(self):
        backups = list_backups()  # devuelve lista de nombres
        self.backup_table.setRowCount(len(backups))
        for row, filename in enumerate(backups):
            # Extraer fecha del nombre: store_YYYYMMDD_HHMMSS.db
            parts = filename.replace("store_", "").replace(".db", "").split("_")
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1]
                fecha = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
            else:
                fecha = "Desconocida"
            # Tamaño del archivo
            path = os.path.join("backups", filename)
            size_kb = round(os.path.getsize(path) / 1024, 1)
            self.backup_table.setItem(row, 0, QTableWidgetItem(filename))
            self.backup_table.setItem(row, 1, QTableWidgetItem(fecha))
            self.backup_table.setItem(row, 2, QTableWidgetItem(f"{size_kb} KB"))

    def restore_selected(self, index):
        row = index.row()
        filename = self.backup_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Restaurar respaldo",
                                     f"¿Restaurar la base de datos desde {filename}?\nSe perderán los cambios no respaldados.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                restore_backup(filename)  # usa tu función
                QMessageBox.information(self, "Restauración exitosa", "Base de datos restaurada. Reinicie la aplicación.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo restaurar: {str(e)}")