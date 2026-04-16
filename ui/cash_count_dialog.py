from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QLabel,
    QPushButton, QMessageBox, QHBoxLayout
)
from PySide6.QtCore import Qt
from services.cash_service import close_cash_register, calculate_daily_totals, get_cash_expected
from services.company_service import get_company_settings

class CashCountDialog(QDialog):
    def __init__(self, db, register_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.register_id = register_id
        self.setWindowTitle("Cuadre de Caja - Calculadora")
        self.setModal(True)
        self.setMinimumSize(500, 500)

        layout = QVBoxLayout()

        # Denominaciones CUP
        self.denominations = [1000, 500, 200, 100, 50, 20, 10, 5, 1]
        self.counts = {}
        form = QFormLayout()
        for denom in self.denominations:
            spin = QDoubleSpinBox()
            spin.setRange(0, 1000)
            spin.setDecimals(0)
            spin.setValue(0)
            spin.valueChanged.connect(self.calculate_total)
            form.addRow(f"{denom} CUP x cantidad:", spin)
            self.counts[denom] = spin

        # Monedas extranjeras
        settings = get_company_settings(db)
        self.usd_rate = settings.usd_rate or 24.0
        self.eur_rate = settings.eur_rate or 25.0

        self.usd_spin = QDoubleSpinBox()
        self.usd_spin.setRange(0, 100000)
        self.usd_spin.setDecimals(2)
        self.usd_spin.setPrefix("USD ")
        self.usd_spin.valueChanged.connect(self.calculate_total)
        self.eur_spin = QDoubleSpinBox()
        self.eur_spin.setRange(0, 100000)
        self.eur_spin.setDecimals(2)
        self.eur_spin.setPrefix("EUR ")
        self.eur_spin.valueChanged.connect(self.calculate_total)

        form.addRow(QLabel(f"USD (tasa {self.usd_rate}):"), self.usd_spin)
        form.addRow(QLabel(f"EUR (tasa {self.eur_rate}):"), self.eur_spin)
        layout.addLayout(form)

        # Totales y diferencias
        self.total_label = QLabel("Total contado: 0.00 CUP")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.total_label)

        totals = calculate_daily_totals(db, register_id)
        expected = get_cash_expected(db, register_id)
        self.expected_label = QLabel(f"Efectivo esperado: {expected:.2f} CUP")
        layout.addWidget(self.expected_label)

        self.diff_label = QLabel("Diferencia: 0.00 CUP")
        layout.addWidget(self.diff_label)

        # Botones
        btn_layout = QHBoxLayout()
        self.accept_btn = QPushButton("Cerrar Caja y Guardar")
        self.accept_btn.clicked.connect(self.accept_close)
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.accept_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.calculate_total()

    def calculate_total(self):
        total_cup = 0
        for denom, spin in self.counts.items():
            total_cup += denom * spin.value()
        usd_total = self.usd_spin.value() * self.usd_rate
        eur_total = self.eur_spin.value() * self.eur_rate
        total = total_cup + usd_total + eur_total
        self.total_label.setText(f"Total contado: {total:.2f} CUP")

        expected = get_cash_expected(self.db, self.register_id)
        diff = total - expected
        self.diff_label.setText(f"Diferencia: {diff:+.2f} CUP")
        if diff < 0:
            self.diff_label.setStyleSheet("color: red")
        elif diff > 0:
            self.diff_label.setStyleSheet("color: orange")
        else:
            self.diff_label.setStyleSheet("color: green")

    def accept_close(self):
        total_text = self.total_label.text()
        total = float(total_text.split(":")[1].strip().split()[0])
        notes = "Cuadre manual"
        try:
            close_cash_register(self.db, self.register_id, total, notes)
            QMessageBox.information(self, "Éxito", "Cierre de caja registrado correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cerrar la caja: {str(e)}")