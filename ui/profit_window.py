# ui/profit_window.py - Panel de ganancias (solo admin)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QDateEdit, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from models.sale import Sale
from models.expense import Expense

class ProfitWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Utilidades y Ganancias")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()

        # Título
        title = QLabel("📊 UTILIDADES NETAS")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Filtros por rango de fechas
        filter_group = QGroupBox("Filtrar por período")
        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.filter_btn = QPushButton("Calcular")
        self.filter_btn.clicked.connect(self.calculate_profit)
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Resumen de ganancias
        summary_group = QGroupBox("Resumen")
        summary_layout = QVBoxLayout()
        self.total_sales_label = QLabel("Ventas totales: 0.00 CUP")
        self.total_cost_label = QLabel("Costo de ventas: 0.00 CUP")
        self.gross_profit_label = QLabel("Ganancia bruta: 0.00 CUP")
        self.expenses_label = QLabel("Gastos operativos: 0.00 CUP")
        self.net_profit_label = QLabel("GANANCIA NETA: 0.00 CUP")
        self.net_profit_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2C3E50;")
        for lbl in [self.total_sales_label, self.total_cost_label, self.gross_profit_label,
                    self.expenses_label, self.net_profit_label]:
            summary_layout.addWidget(lbl)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Tabla de ganancias diarias en el período
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Fecha", "Ventas", "Costo", "Ganancia Neta"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("Desglose diario:"))
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.calculate_profit()  # Cargar datos iniciales

    def calculate_profit(self):
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        # Ajustar end para incluir todo el día
        end = datetime.combine(end, datetime.max.time())

        # Ventas en el período
        sales = self.db.query(Sale).filter(Sale.created_at >= start, Sale.created_at <= end).all()
        total_sales = sum(s.total for s in sales)
        total_cost = sum(s.total_cost for s in sales)
        gross_profit = total_sales - total_cost

        # Gastos operativos (solo los de fuente 'caja' o todos? Para ganancia neta restamos todos los gastos)
        expenses = self.db.query(Expense).filter(Expense.date >= start, Expense.date <= end).all()
        total_expenses = sum(e.amount for e in expenses)
        net_profit = gross_profit - total_expenses

        self.total_sales_label.setText(f"Ventas totales: {total_sales:.2f} CUP")
        self.total_cost_label.setText(f"Costo de ventas: {total_cost:.2f} CUP")
        self.gross_profit_label.setText(f"Ganancia bruta: {gross_profit:.2f} CUP")
        self.expenses_label.setText(f"Gastos operativos: {total_expenses:.2f} CUP")
        self.net_profit_label.setText(f"GANANCIA NETA: {net_profit:.2f} CUP")
        if net_profit >= 0:
            self.net_profit_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        else:
            self.net_profit_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")

        # Desglose diario (agrupar por fecha)
        daily_data = {}
        for s in sales:
            day = s.created_at.date()
            daily_data.setdefault(day, {"sales": 0, "cost": 0})
            daily_data[day]["sales"] += s.total
            daily_data[day]["cost"] += s.total_cost
        # Añadir gastos diarios
        for e in expenses:
            day = e.date.date()
            daily_data.setdefault(day, {"sales": 0, "cost": 0, "expenses": 0})
            daily_data[day]["expenses"] = daily_data[day].get("expenses", 0) + e.amount

        # Ordenar por fecha
        sorted_days = sorted(daily_data.keys())
        self.table.setRowCount(len(sorted_days))
        for row, day in enumerate(sorted_days):
            data = daily_data[day]
            sales_day = data["sales"]
            cost_day = data["cost"]
            expenses_day = data.get("expenses", 0)
            net_day = sales_day - cost_day - expenses_day
            self.table.setItem(row, 0, QTableWidgetItem(day.strftime("%Y-%m-%d")))
            self.table.setItem(row, 1, QTableWidgetItem(f"{sales_day:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{cost_day:.2f}"))
            net_item = QTableWidgetItem(f"{net_day:.2f}")
            if net_day >= 0:
                net_item.setForeground(Qt.GlobalColor.green)
            else:
                net_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, net_item)