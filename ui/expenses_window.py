# ui/expenses_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QComboBox, QDoubleSpinBox,
    QDateEdit, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from services.expense_service import create_expense, get_expenses, delete_expense
from datetime import datetime

class ExpensesWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Registro de Gastos")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("background-color: #F5F7FA;")

        main_layout = QVBoxLayout()

        # --- Panel de formulario para nuevo gasto ---
        form_group = QGroupBox("📝 Nuevo Gasto")
        form_group.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
        """)
        form_group.setMaximumHeight(250)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Ej: Pago de luz, compra de suministros")
        self.desc_input.setMinimumHeight(35)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 1000000)
        self.amount_input.setPrefix("CUP ")
        self.amount_input.setMinimumHeight(35)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["caja", "fondo"])
        self.source_combo.setMinimumHeight(35)

        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setMinimumHeight(35)

        self.save_btn = QPushButton("💾 Registrar Gasto")
        self.save_btn.setStyleSheet("background-color: #4A90E2; border-radius: 6px; padding: 8px;")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self.add_expense)

        form_layout.addRow("Descripción:", self.desc_input)
        form_layout.addRow("Monto:", self.amount_input)
        form_layout.addRow("Fuente:", self.source_combo)
        form_layout.addRow("Fecha:", self.date_input)
        form_layout.addRow("", self.save_btn)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # --- Tabla de gastos existentes ---
        main_layout.addWidget(QLabel("📋 Historial de Gastos"))
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Descripción", "Monto", "Fuente", "Fecha"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)

        # --- Botones de acción ---
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Refrescar")
        self.refresh_btn.clicked.connect(self.load_expenses)
        self.delete_btn = QPushButton("🗑 Eliminar seleccionado")
        self.delete_btn.setStyleSheet("background-color: #E74C3C;")
        self.delete_btn.clicked.connect(self.delete_expense)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # Cargar datos iniciales
        self.load_expenses()

    def add_expense(self):
        desc = self.desc_input.text().strip()
        if not desc:
            QMessageBox.warning(self, "Datos incompletos", "Ingrese una descripción.")
            return
        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "Monto inválido", "El monto debe ser mayor a cero.")
            return
        source = self.source_combo.currentText()
        expense_date = self.date_input.date().toPython()
        try:
            expense = create_expense(self.db, desc, amount, source, self.user.id)
            expense.date = expense_date
            self.db.commit()
            QMessageBox.information(self, "Éxito", "Gasto registrado correctamente.")
            self.desc_input.clear()
            self.amount_input.setValue(0)
            self.date_input.setDate(QDate.currentDate())
            self.load_expenses()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar el gasto: {str(e)}")

    def load_expenses(self):
        """Carga todos los gastos y los muestra en la tabla."""
        expenses = get_expenses(self.db)
        self.table.setRowCount(len(expenses))
        for row, exp in enumerate(expenses):
            self.table.setItem(row, 0, QTableWidgetItem(str(exp.id)))
            self.table.setItem(row, 1, QTableWidgetItem(exp.description))
            self.table.setItem(row, 2, QTableWidgetItem(f"{exp.amount:.2f} CUP"))
            self.table.setItem(row, 3, QTableWidgetItem(exp.source))
            date_str = exp.date.strftime("%Y-%m-%d %H:%M") if exp.date else ""
            self.table.setItem(row, 4, QTableWidgetItem(date_str))
        if not expenses:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 5)
            self.table.setItem(0, 0, QTableWidgetItem("No hay gastos registrados."))

    def delete_expense(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un gasto para eliminar.")
            return
        expense_id = int(self.table.item(current_row, 0).text())
        if self.user.role != "admin":
            QMessageBox.warning(self, "Permiso denegado", "Solo el administrador puede eliminar gastos.")
            return
        reply = QMessageBox.question(self, "Confirmar eliminación", "¿Eliminar este gasto permanentemente?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success = delete_expense(self.db, expense_id)
            if success:
                QMessageBox.information(self, "Eliminado", "Gasto eliminado.")
                self.load_expenses()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el gasto.")