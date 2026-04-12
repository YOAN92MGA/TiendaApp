from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QDateEdit, QLabel, QMessageBox
)
from PySide6.QtCore import QDate
from services.cash_service import get_movements_by_register, add_movement
from ui.cash_movement_dialog import CashMovementDialog

class CashMovementsView(QWidget):
    def __init__(self, db, register_id, register_name):
        super().__init__()
        self.db = db
        self.register_id = register_id
        self.register_name = register_name
        self.setWindowTitle(f"Movimientos - {register_name}")
        self.setStyleSheet("background-color: #F5F7FA;")
        self.resize(800, 500)

        layout = QVBoxLayout()

        # Filtros de fecha
        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.end_date)
        self.filter_btn = QPushButton("Filtrar")
        self.filter_btn.clicked.connect(self.load_movements)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Botón para nuevo movimiento
        self.add_btn = QPushButton("➕ Nuevo movimiento (extracción, compra divisa, remesa)")
        self.add_btn.clicked.connect(self.add_movement)
        layout.addWidget(self.add_btn)

        # Tabla de movimientos
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha", "Tipo", "Monto", "Moneda", "Referencia", "Descripción"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_movements()

    def load_movements(self):
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        movements = get_movements_by_register(self.db, self.register_id, start, end)
        self.table.setRowCount(len(movements))
        for row, mov in enumerate(movements):
            self.table.setItem(row, 0, QTableWidgetItem(str(mov.id)))
            self.table.setItem(row, 1, QTableWidgetItem(mov.created_at.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 2, QTableWidgetItem(mov.type))
            self.table.setItem(row, 3, QTableWidgetItem(f"{mov.amount:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(mov.currency))
            self.table.setItem(row, 5, QTableWidgetItem(str(mov.reference_id) if mov.reference_id else ""))
            self.table.setItem(row, 6, QTableWidgetItem(mov.description or ""))

    def add_movement(self):
        dialog = CashMovementDialog(self.db, self.register_id, self)
        if dialog.exec():
            self.load_movements()