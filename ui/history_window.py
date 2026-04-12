# ui/history_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from services.history_service import get_transactions, get_transaction_types, get_all_users
from datetime import date, timedelta

class HistoryWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Historial de Transacciones")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()

        # Panel de filtros
        filter_layout = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("Todos")
        for t in get_transaction_types(self.db):
            self.type_combo.addItem(t)
        
        self.user_combo = QComboBox()
        self.user_combo.addItem("Todos")
        users = get_all_users(self.db)
        for u in users:
            self.user_combo.addItem(u.username, u.id)   # <--- CORREGIDO
        
        self.filter_btn = QPushButton("Filtrar")
        self.filter_btn.clicked.connect(self.load_transactions)
        
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(QLabel("Tipo:"))
        filter_layout.addWidget(self.type_combo)
        filter_layout.addWidget(QLabel("Usuario:"))
        filter_layout.addWidget(self.user_combo)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Tabla de transacciones
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Fecha", "Tipo", "Producto", "Código", "Cantidad", "Precio", "Usuario"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_transactions()

    def load_transactions(self):
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        trans_type = self.type_combo.currentText()
        if trans_type == "Todos":
            trans_type = None
        user_id = self.user_combo.currentData()
        if user_id is None:
            user_id = None
        
        transactions = get_transactions(self.db, start, end, trans_type, user_id)
        self.table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(str(t["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(t["date"].strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 2, QTableWidgetItem(t["type"]))
            self.table.setItem(row, 3, QTableWidgetItem(t["product_name"]))
            self.table.setItem(row, 4, QTableWidgetItem(t["product_code"]))
            self.table.setItem(row, 5, QTableWidgetItem(str(t["quantity"])))
            price_str = f"{t['price']:.2f}" if t['price'] else ""
            self.table.setItem(row, 6, QTableWidgetItem(price_str))
            self.table.setItem(row, 7, QTableWidgetItem(t["user"]))
        if not transactions:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 8)
            self.table.setItem(0, 0, QTableWidgetItem("No hay transacciones en el período seleccionado."))