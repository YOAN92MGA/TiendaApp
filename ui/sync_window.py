# ui/sync_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QFileDialog, QMessageBox, QDateEdit, QComboBox,
    QFormLayout, QDialog, QDialogButtonBox, QGroupBox
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import Session
from datetime import date, timedelta
from services.sync_service import (
    export_inventory_to_csv, import_inventory_from_csv,
    export_movements_to_csv, import_movements_from_csv
)
from services.sales_export_service import export_sales_to_csv
from services.sales_import_service import import_sales_from_csv
from services.cash_service import get_registers

class SyncWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Sincronización entre Puntos de Venta")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Pestaña 1: Inventario
        self.inventory_tab = QWidget()
        self.setup_inventory_tab()
        self.tabs.addTab(self.inventory_tab, "📦 Inventario")

        # Pestaña 2: Ventas
        self.sales_tab = QWidget()
        self.setup_sales_tab()
        self.tabs.addTab(self.sales_tab, "🛒 Ventas")

        # Pestaña 3: Movimientos de Caja
        self.cash_tab = QWidget()
        self.setup_cash_tab()
        self.tabs.addTab(self.cash_tab, "💰 Movimientos de Caja")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # ========== INVENTARIO ==========
    def setup_inventory_tab(self):
        layout = QVBoxLayout(self.inventory_tab)

        # Exportar inventario
        group_export = QGroupBox("Exportar inventario (para máquinas secundarias)")
        group_export_layout = QVBoxLayout()
        btn_export_inv = QPushButton("📤 Exportar inventario actual a CSV")
        btn_export_inv.clicked.connect(self.export_inventory)
        group_export_layout.addWidget(btn_export_inv)
        group_export.setLayout(group_export_layout)
        layout.addWidget(group_export)

        # Importar inventario (para máquinas secundarias)
        group_import = QGroupBox("Importar inventario (actualizar stock local desde archivo)")
        group_import_layout = QVBoxLayout()
        btn_import_inv = QPushButton("📥 Importar inventario desde CSV")
        btn_import_inv.clicked.connect(self.import_inventory)
        group_import_layout.addWidget(btn_import_inv)
        group_import.setLayout(group_import_layout)
        layout.addWidget(group_import)

        layout.addStretch()

    # ========== VENTAS ==========
    def setup_sales_tab(self):
        layout = QVBoxLayout(self.sales_tab)

        # Exportar ventas (desde máquina secundaria)
        group_export = QGroupBox("Exportar ventas (desde esta máquina)")
        group_export_layout = QVBoxLayout()
        form = QFormLayout()
        self.sales_date_edit = QDateEdit()
        self.sales_date_edit.setDate(QDate.currentDate())
        self.sales_date_edit.setCalendarPopup(True)
        form.addRow("Fecha de ventas a exportar:", self.sales_date_edit)
        group_export_layout.addLayout(form)
        btn_export_sales = QPushButton("📄 Exportar ventas del día a CSV")
        btn_export_sales.clicked.connect(self.export_sales)
        group_export_layout.addWidget(btn_export_sales)
        group_export.setLayout(group_export_layout)
        layout.addWidget(group_export)

        # Importar ventas (en máquina principal)
        group_import = QGroupBox("Importar ventas (desde archivo de otra máquina)")
        group_import_layout = QVBoxLayout()
        btn_import_sales = QPushButton("📂 Importar ventas desde CSV")
        btn_import_sales.clicked.connect(self.import_sales)
        group_import_layout.addWidget(btn_import_sales)
        group_import.setLayout(group_import_layout)
        layout.addWidget(group_import)

        layout.addStretch()

    # ========== MOVIMIENTOS DE CAJA ==========
    def setup_cash_tab(self):
        layout = QVBoxLayout(self.cash_tab)

        # Seleccionar caja origen
        form = QFormLayout()
        self.cash_register_combo = QComboBox()
        self.load_cash_registers()
        form.addRow("Caja:", self.cash_register_combo)
        layout.addLayout(form)

        # Exportar movimientos
        group_export = QGroupBox("Exportar movimientos de caja")
        group_export_layout = QVBoxLayout()
        date_range_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        date_range_layout.addWidget(QLabel("Desde:"))
        date_range_layout.addWidget(self.start_date_edit)
        date_range_layout.addWidget(QLabel("Hasta:"))
        date_range_layout.addWidget(self.end_date_edit)
        group_export_layout.addLayout(date_range_layout)
        btn_export_cash = QPushButton("📤 Exportar movimientos a CSV")
        btn_export_cash.clicked.connect(self.export_cash_movements)
        group_export_layout.addWidget(btn_export_cash)
        group_export.setLayout(group_export_layout)
        layout.addWidget(group_export)

        # Importar movimientos (en máquina principal)
        group_import = QGroupBox("Importar movimientos de caja (desde archivo)")
        group_import_layout = QVBoxLayout()
        btn_import_cash = QPushButton("📥 Importar movimientos desde CSV")
        btn_import_cash.clicked.connect(self.import_cash_movements)
        group_import_layout.addWidget(btn_import_cash)
        group_import.setLayout(group_import_layout)
        layout.addWidget(group_import)

        layout.addStretch()

    def load_cash_registers(self):
        registers = get_registers(self.db)
        self.cash_register_combo.clear()
        for reg in registers:
            self.cash_register_combo.addItem(f"{reg.name} (ID:{reg.id})", reg.id)

    # ----- Funciones de inventario -----
    def export_inventory(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar inventario", "inventario.csv", "CSV (*.csv)")
        if filepath:
            try:
                export_inventory_to_csv(self.db, filepath)
                QMessageBox.information(self, "Éxito", f"Inventario exportado a {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def import_inventory(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de inventario", "", "CSV (*.csv)")
        if filepath:
            try:
                import_inventory_from_csv(self.db, filepath)
                QMessageBox.information(self, "Éxito", "Inventario actualizado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ----- Funciones de ventas -----
    def export_sales(self):
        target_date = self.sales_date_edit.date().toPython()
        filepath, _ = QFileDialog.getSaveFileName(self, f"Guardar ventas del {target_date}", f"ventas_{target_date}.csv", "CSV (*.csv)")
        if filepath:
            try:
                count = export_sales_to_csv(self.db, filepath, target_date)
                QMessageBox.information(self, "Éxito", f"Se exportaron {count} ventas a {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def import_sales(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de ventas", "", "CSV (*.csv)")
        if filepath:
            try:
                count = import_sales_from_csv(self.db, filepath, self.user.id)
                QMessageBox.information(self, "Éxito", f"Se importaron {count} ventas correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ----- Funciones de caja -----
    def export_cash_movements(self):
        register_id = self.cash_register_combo.currentData()
        if not register_id:
            QMessageBox.warning(self, "Error", "Seleccione una caja.")
            return
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()
        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar movimientos de caja", f"movimientos_caja_{register_id}_{start_date}_{end_date}.csv", "CSV (*.csv)")
        if filepath:
            try:
                export_movements_to_csv(self.db, register_id, filepath, start_date, end_date)
                QMessageBox.information(self, "Éxito", f"Movimientos exportados a {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def import_cash_movements(self):
        # Primero seleccionar caja destino (en máquina principal)
        registers = get_registers(self.db)
        if not registers:
            QMessageBox.warning(self, "Error", "No hay cajas registradas en esta máquina.")
            return
        # Diálogo para elegir caja destino
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleccionar caja destino")
        layout = QVBoxLayout()
        form = QFormLayout()
        combo = QComboBox()
        for reg in registers:
            combo.addItem(f"{reg.name} (ID:{reg.id})", reg.id)
        form.addRow("Caja destino:", combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        if dialog.exec() != QDialog.Accepted:
            return
        target_register_id = combo.currentData()

        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de movimientos de caja", "", "CSV (*.csv)")
        if filepath:
            try:
                import_movements_from_csv(self.db, target_register_id, filepath)
                QMessageBox.information(self, "Éxito", "Movimientos importados correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))