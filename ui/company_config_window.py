# ui/company_config_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QDoubleSpinBox, QTextEdit, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt
from services.company_service import get_company_settings, update_company_settings

class CompanyConfigWindow(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Configuración de la Empresa")
        self.setStyleSheet("background-color: #F5F7FA;")
        
        layout = QVBoxLayout()
        
        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.company_name_input = QLineEdit()
        self.nif_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.tax_rate_input = QDoubleSpinBox()
        self.tax_rate_input.setRange(0, 100)
        self.tax_rate_input.setSuffix(" %")
        self.currency_input = QLineEdit()
        self.receipt_footer_input = QTextEdit()
        self.receipt_footer_input.setMaximumHeight(80)
        
        # Logo
        logo_layout = QHBoxLayout()
        self.logo_path_input = QLineEdit()
        self.logo_path_input.setReadOnly(True)
        self.logo_browse_btn = QPushButton("Seleccionar logo")
        self.logo_browse_btn.clicked.connect(self.browse_logo)
        logo_layout.addWidget(self.logo_path_input)
        logo_layout.addWidget(self.logo_browse_btn)
        
        form_layout.addRow("Nombre de la empresa:", self.company_name_input)
        form_layout.addRow("NIF/CIF:", self.nif_input)
        form_layout.addRow("Dirección:", self.address_input)
        form_layout.addRow("Teléfono:", self.phone_input)
        form_layout.addRow("Email:", self.email_input)
        form_layout.addRow("Logo:", logo_layout)
        form_layout.addRow("Impuesto general (%):", self.tax_rate_input)
        form_layout.addRow("Moneda:", self.currency_input)
        form_layout.addRow("Texto pie de tiquete:", self.receipt_footer_input)
        
        layout.addLayout(form_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Guardar cambios")
        self.save_btn.setStyleSheet("background-color: #4A90E2; border-radius: 6px; padding: 8px;")
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn = QPushButton("❌ Cancelar")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Cargar datos actuales
        self.load_settings()
    
    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar logo", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.logo_path_input.setText(file_path)
    
    def load_settings(self):
        settings = get_company_settings(self.db)
        self.company_name_input.setText(settings.company_name or "")
        self.nif_input.setText(settings.nif or "")
        self.address_input.setText(settings.address or "")
        self.phone_input.setText(settings.phone or "")
        self.email_input.setText(settings.email or "")
        self.tax_rate_input.setValue(settings.tax_rate or 0.0)
        self.currency_input.setText(settings.currency or "CUP")
        self.receipt_footer_input.setPlainText(settings.receipt_footer or "¡Gracias por su compra!")
        self.logo_path_input.setText(settings.logo_path or "")
    
    def save_settings(self):
        try:
            update_company_settings(
                self.db,
                company_name=self.company_name_input.text().strip(),
                nif=self.nif_input.text().strip(),
                address=self.address_input.text().strip(),
                phone=self.phone_input.text().strip(),
                email=self.email_input.text().strip(),
                logo_path=self.logo_path_input.text().strip() or None,
                tax_rate=self.tax_rate_input.value(),
                currency=self.currency_input.text().strip(),
                receipt_footer=self.receipt_footer_input.toPlainText().strip()
            )
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente.")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {str(e)}")