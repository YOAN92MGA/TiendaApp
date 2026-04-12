from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QDialogButtonBox, QLabel
)
from services.cash_service import add_movement

class CashMovementDialog(QDialog):
    def __init__(self, db, register_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.register_id = register_id
        self.setWindowTitle("Registrar movimiento de caja")
        self.setModal(True)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["extraction", "currency_purchase", "remittance"])
        # Personalizar textos
        self.type_combo.setItemText(0, "Extracción")
        self.type_combo.setItemText(1, "Compra de divisa")
        self.type_combo.setItemText(2, "Remesa")
        form.addRow("Tipo:", self.type_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 1000000)
        self.amount_spin.setPrefix("$ ")
        form.addRow("Monto:", self.amount_spin)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["CUP", "USD", "EUR"])
        form.addRow("Moneda:", self.currency_combo)

        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("Opcional: ID de venta, compra, etc.")
        form.addRow("Referencia:", self.reference_input)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setPlaceholderText("Descripción detallada (ej. pago de salario, compra de mercancía, etc.)")
        form.addRow("Descripción:", self.desc_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        # Validar
        if self.amount_spin.value() <= 0:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "El monto debe ser mayor a cero.")
            return
        try:
            add_movement(
                db=self.db,
                register_id=self.register_id,
                movement_type=self.type_combo.currentText(),
                amount=self.amount_spin.value(),
                currency=self.currency_combo.currentText(),
                description=self.desc_input.toPlainText(),
                reference_id=int(self.reference_input.text()) if self.reference_input.text().isdigit() else None
            )
            super().accept()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {str(e)}")