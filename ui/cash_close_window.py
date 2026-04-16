# ui/cash_close_window.py - Con pestañas
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QSpinBox, QLineEdit, QComboBox, QScrollArea, QFrame, QGridLayout,
    QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from models.sale import Sale
from services.cash_service import (
    get_or_create_main_register, calculate_daily_totals,
    get_cash_expected, close_cash_register
)

class CashCloseWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Cierre de Caja")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.register = get_or_create_main_register(db)
        self.register_id = self.register.id

        # Pestañas
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { height: 35px; width: 180px; font-size: 13px; }")

        # Pestaña 1: Resumen del día
        self.summary_tab = QWidget()
        self.setup_summary_tab()
        self.tabs.addTab(self.summary_tab, "📋 Resumen del día")

        # Pestaña 2: Conteo de efectivo real
        self.count_tab = QWidget()
        self.setup_count_tab()
        self.tabs.addTab(self.count_tab, "💰 Conteo de efectivo real")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Cargar datos iniciales
        self.refresh_summary()

    def setup_summary_tab(self):
        layout = QVBoxLayout(self.summary_tab)

        # Info de caja
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>Caja:</b> {self.register.name}"))
        info_layout.addWidget(QLabel(f"<b>Fecha:</b> {date.today().strftime('%d/%m/%Y')}"))
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Tabla de ventas
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(2)
        self.sales_table.setHorizontalHeaderLabels(["Método de pago", "Total"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setMaximumHeight(150)
        layout.addWidget(QLabel("<b>Ventas del día</b>"))
        layout.addWidget(self.sales_table)

        # Datos adicionales
        stats_layout = QGridLayout()
        self.expenses_label = QLabel("Gastos en efectivo: 0.00 CUP")
        self.withdrawals_label = QLabel("Extracciones: 0.00 CUP")
        self.remittances_label = QLabel("Remesas: 0.00 CUP")
        self.usd_label = QLabel("USD comprados: 0.00")
        self.eur_label = QLabel("EUR comprados: 0.00")
        self.zelle_label = QLabel("Pagos Zelle: 0.00 USD")
        for i, lbl in enumerate([self.expenses_label, self.withdrawals_label, self.remittances_label,
                                 self.usd_label, self.eur_label, self.zelle_label]):
            lbl.setStyleSheet("font-size: 12px; padding: 4px;")
            stats_layout.addWidget(lbl, i//2, i%2)
        layout.addLayout(stats_layout)

        # Efectivo esperado (se mostrará aquí también)
        self.expected_cash_label = QLabel("Efectivo esperado: 0.00 CUP")
        self.expected_cash_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px;")
        layout.addWidget(self.expected_cash_label)

        layout.addStretch()

        # Botón refrescar datos
        refresh_btn = QPushButton("🔄 Refrescar datos")
        refresh_btn.clicked.connect(self.refresh_summary)
        layout.addWidget(refresh_btn)

    def setup_count_tab(self):
        layout = QVBoxLayout(self.count_tab)

        # Calculadora de billetes CUP
        cup_frame = QFrame()
        cup_frame.setFrameShape(QFrame.StyledPanel)
        cup_frame.setStyleSheet("background-color: white; border-radius: 12px; padding: 10px;")
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
            spin.setFixedHeight(30)
            spin.setFixedWidth(80)
            spin.valueChanged.connect(self.calculate_total)
            cup_grid.addWidget(QLabel(f"{denom} CUP:"), row, col)
            cup_grid.addWidget(spin, row, col+1)
            self.cup_spins[denom] = spin
            col += 2
            if col >= 6:
                col = 0
                row += 1
        cup_layout.addLayout(cup_grid)
        layout.addWidget(cup_frame)

        # Divisas
        currencies_frame = QFrame()
        currencies_frame.setFrameShape(QFrame.StyledPanel)
        currencies_frame.setStyleSheet("background-color: white; border-radius: 12px; padding: 10px;")
        currencies_layout = QVBoxLayout(currencies_frame)
        currencies_layout.addWidget(QLabel("<b>Divisas</b>"))

        # USD
        usd_row = QHBoxLayout()
        usd_row.addWidget(QLabel("USD:"))
        self.usd_amount = QDoubleSpinBox()
        self.usd_amount.setRange(0, 1000000)
        self.usd_amount.setValue(0)
        self.usd_amount.setPrefix("$ ")
        self.usd_amount.setFixedHeight(30)
        self.usd_amount.setFixedWidth(120)
        self.usd_amount.valueChanged.connect(self.calculate_total)
        usd_row.addWidget(self.usd_amount)
        usd_row.addWidget(QLabel("Tasa CUP/USD:"))
        self.usd_rate = QDoubleSpinBox()
        self.usd_rate.setRange(0, 1000)
        self.usd_rate.setValue(24.0)
        self.usd_rate.setDecimals(2)
        self.usd_rate.setFixedHeight(30)
        self.usd_rate.setFixedWidth(100)
        self.usd_rate.valueChanged.connect(self.calculate_total)
        usd_row.addWidget(self.usd_rate)
        usd_row.addStretch()
        currencies_layout.addLayout(usd_row)

        # EUR
        eur_row = QHBoxLayout()
        eur_row.addWidget(QLabel("EUR:"))
        self.eur_amount = QDoubleSpinBox()
        self.eur_amount.setRange(0, 1000000)
        self.eur_amount.setValue(0)
        self.eur_amount.setPrefix("€ ")
        self.eur_amount.setFixedHeight(30)
        self.eur_amount.setFixedWidth(120)
        self.eur_amount.valueChanged.connect(self.calculate_total)
        eur_row.addWidget(self.eur_amount)
        eur_row.addWidget(QLabel("Tasa CUP/EUR:"))
        self.eur_rate = QDoubleSpinBox()
        self.eur_rate.setRange(0, 1000)
        self.eur_rate.setValue(26.0)
        self.eur_rate.setDecimals(2)
        self.eur_rate.setFixedHeight(30)
        self.eur_rate.setFixedWidth(100)
        self.eur_rate.valueChanged.connect(self.calculate_total)
        eur_row.addWidget(self.eur_rate)
        eur_row.addStretch()
        currencies_layout.addLayout(eur_row)

        layout.addWidget(currencies_frame)

        # Totales y diferencia
        totals_frame = QFrame()
        totals_frame.setStyleSheet("background-color: #E8F0FE; border-radius: 10px; padding: 10px;")
        totals_layout = QVBoxLayout(totals_frame)
        self.total_cash_label = QLabel("Total efectivo contado: 0.00 CUP")
        self.total_cash_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.difference_label = QLabel("Diferencia: 0.00 CUP")
        self.difference_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        totals_layout.addWidget(self.total_cash_label)
        totals_layout.addWidget(self.difference_label)
        layout.addWidget(totals_frame)

        # Botón finalizar cierre
        self.close_btn = QPushButton("🔒 FINALIZAR CIERRE DE CAJA")
        self.close_btn.setMinimumHeight(60)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        self.close_btn.clicked.connect(self.finalize_close)
        layout.addWidget(self.close_btn)

    def refresh_summary(self):
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())

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

        totals = calculate_daily_totals(self.db, self.register_id, today)
        self.expenses_label.setText(f"Gastos en efectivo: {totals['total_expenses']:.2f} CUP")
        self.withdrawals_label.setText(f"Extracciones: {totals['total_extractions']:.2f} CUP")
        self.remittances_label.setText(f"Remesas: {totals['remittances']:.2f} CUP")
        self.usd_label.setText(f"USD comprados: {totals['usd_purchased']:.2f}")
        self.eur_label.setText(f"EUR comprados: {totals['eur_purchased']:.2f}")
        self.zelle_label.setText(f"Pagos Zelle: {totals['zelle_purchases']:.2f} USD")

        expected = get_cash_expected(self.db, self.register_id, today)
        self.expected_cash_label.setText(f"Efectivo esperado: {expected:.2f} CUP")

    def calculate_total(self):
        total_cup = sum(denom * self.cup_spins[denom].value() for denom in self.cup_spins)
        usd_total = self.usd_amount.value() * self.usd_rate.value()
        eur_total = self.eur_amount.value() * self.eur_rate.value()
        total = total_cup + usd_total + eur_total
        self.total_cash_label.setText(f"Total efectivo contado: {total:.2f} CUP")

        # Obtener esperado desde la pestaña resumen
        expected_text = self.expected_cash_label.text().split(":")[-1].strip().replace(" CUP", "")
        expected = float(expected_text) if expected_text else 0.0
        diff = total - expected
        self.difference_label.setText(f"Diferencia: {diff:+.2f} CUP")
        if diff > 0:
            self.difference_label.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
        elif diff < 0:
            self.difference_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
        else:
            self.difference_label.setStyleSheet("color: black; font-size: 16px; font-weight: bold;")

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