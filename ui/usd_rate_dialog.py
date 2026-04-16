from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QDialogButtonBox, QMessageBox
from services.company_service import get_company_settings, update_company_settings

class UsdRateDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Actualizar tasas de cambio")
        self.setModal(True)

        layout = QVBoxLayout()
        form = QFormLayout()

        settings = get_company_settings(db)
        self.usd_spin = QDoubleSpinBox()
        self.usd_spin.setRange(0, 200)
        self.usd_spin.setDecimals(2)
        self.usd_spin.setValue(settings.usd_rate or 24.0)
        self.usd_spin.setSuffix(" CUP")
        form.addRow("Tasa USD:", self.usd_spin)

        self.eur_spin = QDoubleSpinBox()
        self.eur_spin.setRange(0, 200)
        self.eur_spin.setDecimals(2)
        self.eur_spin.setValue(settings.eur_rate or 25.0)
        self.eur_spin.setSuffix(" CUP")
        form.addRow("Tasa EUR:", self.eur_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def save(self):
        try:
            update_company_settings(self.db,
                                    usd_rate=self.usd_spin.value(),
                                    eur_rate=self.eur_spin.value())
            QMessageBox.information(self, "Éxito", "Tasas actualizadas correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))