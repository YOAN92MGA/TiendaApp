# ui/cash_close_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QSpinBox, QLineEdit, QComboBox, QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from models.sale import Sale
from models.expense import Expense
from services.cash_service import (
    get_or_create_main_register, get_daily_movements, calculate_daily_totals,
    get_cash_expected, register_withdrawal, register_expense, register_currency_purchase,
    register_remittance, register_zelle_purchase, close_cash_register
)

class CashCloseWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Cierre de Caja")
        self.setMinimumSize(1100, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        # Obtener o crear caja principal
        self.register = get_or_create_main_register(db)
        self.register_id = self.register.id

        # Layout principal con scroll
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        main_scroll.setWidget(container)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_scroll)

        # Título
        title = QLabel("🧾 Cierre de Caja")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2C3E50; margin: 10px;")
        layout.addWidget(title)

        # Información de caja y fecha
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Caja: {self.register.name}"))
        info_layout.addWidget(QLabel(f"Fecha: {date.today().strftime('%d/%m/%Y')}"))
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # ===== Resumen del día =====
        summary_group = QGroupBox("📊 Resumen del día")
        summary_layout = QVBoxLayout()
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(2)
        self.sales_table.setHorizontalHeaderLabels(["Método", "Total"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setMaximumHeight(150)
        summary_layout.addWidget(self.sales_table)

        # Datos adicionales
        self.expenses_label = QLabel("Gastos en efectivo: 0.00 CUP")
        self.withdrawals_label = QLabel("Extracciones: 0.00 CUP")
        self.remittances_label = QLabel("Remesas: 0.00 CUP")
        self.usd_label = QLabel("USD comprados: 0.00")
        self.eur_label = QLabel("EUR comprados: 0.00")
        self.zelle_label = QLabel("Pagos Zelle: 0.00 USD")
        for lbl in [self.expenses_label, self.withdrawals_label, self.remittances_label, self.usd_label, self.eur_label, self.zelle_label]:
            summary_layout.addWidget(lbl)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # ===== Calculadora de efectivo real =====
        cash_group = QGroupBox("💰 Conteo de efectivo real")
        cash_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        cash_layout = QVBoxLayout()

        # Moneda Nacional (CUP) con billetes
        cup_frame = QFrame()
        cup_frame.setFrameShape(QFrame.StyledPanel)
        cup_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        cup_layout = QVBoxLayout(cup_frame)
        cup_layout.addWidget(QLabel("<b>Moneda Nacional (CUP)</b>"))
        cup_grid = QGridLayout()
        cup_denoms = [1000, 500, 200, 100, 50, 20, 10, 5, 1]
        self.cup_spins = {}
        row, col = 0, 0
        for denom in cup_denoms:
            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(0)
            spin.valueChanged.connect(self.calculate_total)
            cup_grid.addWidget(QLabel(f"{denom} CUP:"), row, col)
            cup_grid.addWidget(spin, row, col+1)
            self.cup_spins[denom] = spin
            col += 2
            if col >= 6:
                col = 0
                row += 1
        cup_layout.addLayout(cup_grid)
        cash_layout.addWidget(cup_frame)

        # Divisas (USD, EUR) con campo de cantidad y tasa de cambio
        currencies_frame = QFrame()
        currencies_frame.setFrameShape(QFrame.StyledPanel)
        currencies_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        currencies_layout = QVBoxLayout(currencies_frame)
        currencies_layout.addWidget(QLabel("<b>Divisas</b>"))
        
        # USD
        usd_layout = QHBoxLayout()
        usd_layout.addWidget(QLabel("USD:"))
        self.usd_amount = QDoubleSpinBox()
        self.usd_amount.setRange(0, 1000000)
        self.usd_amount.setValue(0)
        self.usd_amount.setPrefix("$ ")
        self.usd_amount.valueChanged.connect(self.calculate_total)
        usd_layout.addWidget(self.usd_amount)
        usd_layout.addWidget(QLabel("Tasa CUP/USD:"))
        self.usd_rate = QDoubleSpinBox()
        self.usd_rate.setRange(0, 1000)
        self.usd_rate.setValue(24.0)
        self.usd_rate.setDecimals(2)
        self.usd_rate.valueChanged.connect(self.calculate_total)
        usd_layout.addWidget(self.usd_rate)
        usd_layout.addStretch()
        currencies_layout.addLayout(usd_layout)
        
        # EUR
        eur_layout = QHBoxLayout()
        eur_layout.addWidget(QLabel("EUR:"))
        self.eur_amount = QDoubleSpinBox()
        self.eur_amount.setRange(0, 1000000)
        self.eur_amount.setValue(0)
        self.eur_amount.setPrefix("€ ")
        self.eur_amount.valueChanged.connect(self.calculate_total)
        eur_layout.addWidget(self.eur_amount)
        eur_layout.addWidget(QLabel("Tasa CUP/EUR:"))
        self.eur_rate = QDoubleSpinBox()
        self.eur_rate.setRange(0, 1000)
        self.eur_rate.setValue(26.0)
        self.eur_rate.setDecimals(2)
        self.eur_rate.valueChanged.connect(self.calculate_total)
        eur_layout.addWidget(self.eur_rate)
        eur_layout.addStretch()
        currencies_layout.addLayout(eur_layout)
        
        cash_layout.addWidget(currencies_frame)
        
        # Totales
        self.total_cash_label = QLabel("Total efectivo contado: 0.00 CUP")
        self.total_cash_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.expected_cash_label = QLabel("Efectivo esperado: 0.00 CUP")
        self.difference_label = QLabel("Diferencia: 0.00 CUP")
        self.difference_label.setStyleSheet("font-weight: bold;")
        cash_layout.addWidget(self.total_cash_label)
        cash_layout.addWidget(self.expected_cash_label)
        cash_layout.addWidget(self.difference_label)
        
        cash_group.setLayout(cash_layout)
        layout.addWidget(cash_group)

        # ===== Botones para movimientos =====
        movements_group = QGroupBox("📝 Movimientos de caja")
        movements_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.withdrawal_btn = QPushButton("💰 Extracción de caja")
        self.expense_btn = QPushButton("💸 Gasto en efectivo")
        self.usd_purchase_btn = QPushButton("💵 Compra de USD")
        self.eur_purchase_btn = QPushButton("💶 Compra de EUR")
        self.zelle_btn = QPushButton("💳 Pago por Zelle")
        self.remittance_btn = QPushButton("📲 Remesa recibida")
        for btn in [self.withdrawal_btn, self.expense_btn, self.usd_purchase_btn, self.eur_purchase_btn, self.zelle_btn, self.remittance_btn]:
            btn.clicked.connect(self.open_movement_dialog)
            btn_layout.addWidget(btn)
        movements_layout.addLayout(btn_layout)
        movements_group.setLayout(movements_layout)
        layout.addWidget(movements_group)

        # Botón finalizar cierre
        self.close_btn = QPushButton("🔒 Finalizar cierre de caja")
        self.close_btn.setStyleSheet("background-color: #E74C3C; border-radius: 8px; padding: 12px; font-size: 14px;")
        self.close_btn.clicked.connect(self.finalize_close)
        layout.addWidget(self.close_btn)

        # Cargar datos iniciales
        self.refresh_data()

    def refresh_data(self):
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        # Ventas del día (desde Sale)
        sales = self.db.query(Sale).filter(Sale.created_at >= start, Sale.created_at < end).all()
        total_cash = sum(s.total for s in sales if s.payment_method == "Efectivo")
        total_transfer = sum(s.total for s in sales if s.payment_method == "Transferencia")
        total_zelle = sum(s.total for s in sales if s.payment_method == "Zelle")

        self.sales_table.setRowCount(3)
        self.sales_table.setItem(0, 0, QTableWidgetItem("Efectivo"))
        self.sales_table.setItem(0, 1, QTableWidgetItem(f"{total_cash:.2f} CUP"))
        self.sales_table.setItem(1, 0, QTableWidgetItem("Transferencia"))
        self.sales_table.setItem(1, 1, QTableWidgetItem(f"{total_transfer:.2f} CUP"))
        self.sales_table.setItem(2, 0, QTableWidgetItem("Zelle"))
        self.sales_table.setItem(2, 1, QTableWidgetItem(f"{total_zelle:.2f} CUP"))

        # Gastos y movimientos (desde CashMovement)
        totals = calculate_daily_totals(self.db, self.register_id, today)
        self.expenses_label.setText(f"Gastos en efectivo: {totals['total_expenses']:.2f} CUP")
        self.withdrawals_label.setText(f"Extracciones: {totals['total_extractions']:.2f} CUP")
        self.remittances_label.setText(f"Remesas: {totals['remittances']:.2f} CUP")
        self.usd_label.setText(f"USD comprados: {totals['usd_purchased']:.2f}")
        self.eur_label.setText(f"EUR comprados: {totals['eur_purchased']:.2f}")
        self.zelle_label.setText(f"Pagos Zelle: {totals['zelle_purchases']:.2f} USD")

        expected = get_cash_expected(self.db, self.register_id, today)
        self.expected_cash_label.setText(f"Efectivo esperado: {expected:.2f} CUP")
        self.calculate_total()

    def calculate_total(self):
        total_cup = sum(denom * self.cup_spins[denom].value() for denom in self.cup_spins)
        usd_total = self.usd_amount.value() * self.usd_rate.value()
        eur_total = self.eur_amount.value() * self.eur_rate.value()
        total = total_cup + usd_total + eur_total
        self.total_cash_label.setText(f"Total efectivo contado: {total:.2f} CUP")

        expected_text = self.expected_cash_label.text().split(":")[-1].strip().replace(" CUP", "")
        expected = float(expected_text) if expected_text else 0.0
        diff = total - expected
        self.difference_label.setText(f"Diferencia: {diff:+.2f} CUP")
        if diff > 0:
            self.difference_label.setStyleSheet("color: green; font-weight: bold;")
        elif diff < 0:
            self.difference_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.difference_label.setStyleSheet("color: black;")

    def open_movement_dialog(self):
        sender = self.sender()
        if sender == self.withdrawal_btn:
            self.register_movement("withdrawal", "Extracción de caja", ask_amount=True, ask_reason=True)
        elif sender == self.expense_btn:
            self.register_movement("expense", "Gasto en efectivo", ask_amount=True, ask_reason=True)
        elif sender == self.usd_purchase_btn:
            self.register_movement("usd_purchase", "Compra de USD", ask_amount=True, ask_rate=True)
        elif sender == self.eur_purchase_btn:
            self.register_movement("eur_purchase", "Compra de EUR", ask_amount=True, ask_rate=True)
        elif sender == self.zelle_btn:
            self.register_movement("zelle", "Pago por Zelle", ask_amount=True)
        elif sender == self.remittance_btn:
            self.register_movement("remittance", "Remesa recibida", ask_amount=True)

    def register_movement(self, mov_type, title, ask_amount=False, ask_reason=False, ask_rate=False):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QFormLayout()
        amount_input = QDoubleSpinBox()
        amount_input.setRange(0, 1000000)
        amount_input.setPrefix("CUP " if mov_type in ["withdrawal", "expense", "remittance"] else ("USD " if mov_type == "usd_purchase" else "EUR "))
        amount_input.valueChanged.connect(lambda: None)
        if ask_amount:
            layout.addRow("Monto:", amount_input)
        reason_input = QLineEdit()
        if ask_reason:
            layout.addRow("Motivo:", reason_input)
        rate_input = QDoubleSpinBox()
        rate_input.setRange(0, 1000)
        rate_input.setDecimals(2)
        if ask_rate:
            layout.addRow("Tasa de cambio (CUP/divisa):", rate_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() != QDialog.Accepted:
            return
        amount = amount_input.value()
        if ask_reason:
            reason = reason_input.text()
            if not reason:
                QMessageBox.warning(self, "Error", "Debe especificar el motivo.")
                return
        try:
            if mov_type == "withdrawal":
                register_withdrawal(self.db, self.register_id, amount, reason, self.user.id)
            elif mov_type == "expense":
                register_expense(self.db, self.register_id, amount, reason, self.user.id)
            elif mov_type == "usd_purchase":
                rate = rate_input.value()
                register_currency_purchase(self.db, self.register_id, "USD", amount, rate, self.user.id)
            elif mov_type == "eur_purchase":
                rate = rate_input.value()
                register_currency_purchase(self.db, self.register_id, "EUR", amount, rate, self.user.id)
            elif mov_type == "zelle":
                register_zelle_purchase(self.db, self.register_id, amount, "", self.user.id)
            elif mov_type == "remittance":
                register_remittance(self.db, self.register_id, amount, reason, self.user.id)
            QMessageBox.information(self, "Registrado", "Movimiento registrado correctamente.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def finalize_close(self):
        reply = QMessageBox.question(self, "Cerrar caja", "¿Está seguro de finalizar el cierre de caja?\nNo se podrán modificar movimientos del día después de cerrar.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        total_cup = sum(denom * self.cup_spins[denom].value() for denom in self.cup_spins)
        usd_total = self.usd_amount.value() * self.usd_rate.value()
        eur_total = self.eur_amount.value() * self.eur_rate.value()
        total_real = total_cup + usd_total + eur_total

        bill_details = {
            "cup": {str(k): v.value() for k, v in self.cup_spins.items()},
            "usd": {"amount": self.usd_amount.value(), "rate": self.usd_rate.value()},
            "eur": {"amount": self.eur_amount.value(), "rate": self.eur_rate.value()}
        }
        try:
            close = close_cash_register(self.db, self.register_id, total_real, bill_details, notes="Cierre diario", user_id=self.user.id)
            QMessageBox.information(self, "Cierre completado", f"Cierre de caja #{close.id} guardado.\nDiferencia: {close.difference:+.2f} CUP")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))