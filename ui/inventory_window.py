# ui/inventory_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QSpinBox, QLineEdit, QFormLayout, QDialog, QDialogButtonBox,
    QGroupBox
)
from PySide6.QtWidgets import QInputDialog
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from models.stock_location import StockLocation
from models.product import Product
from services.inventory_service import get_current_stock, apply_adjustment, save_inventory_count

class InventoryWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Inventario Físico y Ajustes")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #F5F7FA;")

        main_layout = QVBoxLayout()

        # Selección de ubicación
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Ubicación:"))
        self.location_combo = QComboBox()
        self.load_locations()
        self.location_combo.currentIndexChanged.connect(self.load_inventory)
        location_layout.addWidget(self.location_combo)
        location_layout.addStretch()
        main_layout.addLayout(location_layout)

        # Tabla de productos
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID Producto", "Nombre", "Stock actual", "Cantidad contada", "Diferencia", "Ajustar"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main_layout.addWidget(QLabel("Productos en la ubicación seleccionada:"))
        main_layout.addWidget(self.table)

        # Botones de acción
        btn_layout = QHBoxLayout()
        self.save_count_btn = QPushButton("💾 Guardar conteo (historial)")
        self.save_count_btn.clicked.connect(self.save_count)
        self.apply_adjustments_btn = QPushButton("⚙️ Aplicar ajustes seleccionados")
        self.apply_adjustments_btn.setStyleSheet("background-color: #4A90E2;")
        self.apply_adjustments_btn.clicked.connect(self.apply_adjustments)
        btn_layout.addWidget(self.save_count_btn)
        btn_layout.addWidget(self.apply_adjustments_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # Diccionario para almacenar los spinboxes y widgets de cada fila
        self.spinboxes = {}
        self.difference_labels = {}
        self.adjust_buttons = {}
        self.current_stock_data = []  # lista de dicts con info de stock

    def load_locations(self):
        """Carga las ubicaciones (Almacén, Piso) en el combo."""
        locations = self.db.query(StockLocation).filter(StockLocation.name.in_(["Almacen", "Piso"])).all()
        for loc in locations:
            self.location_combo.addItem(loc.name, loc.id)

    def load_inventory(self):
        """Carga el stock actual de la ubicación seleccionada."""
        loc_id = self.location_combo.currentData()
        if not loc_id:
            return
        stocks = get_current_stock(self.db, loc_id)
        self.current_stock_data = stocks
        self.table.setRowCount(len(stocks))
        self.spinboxes.clear()
        self.difference_labels.clear()
        self.adjust_buttons.clear()
        for row, stock in enumerate(stocks):
            # Obtener nombre del producto
            product = self.db.query(Product).filter(Product.id == stock["product_id"]).first()
            product_name = product.name if product else "Desconocido"
            self.table.setItem(row, 0, QTableWidgetItem(str(stock["product_id"])))
            self.table.setItem(row, 1, QTableWidgetItem(product_name))
            self.table.setItem(row, 2, QTableWidgetItem(str(stock["quantity"])))
            # Spinbox para cantidad contada
            spin = QSpinBox()
            spin.setRange(0, 999999)
            spin.setValue(stock["quantity"])
            spin.valueChanged.connect(lambda value, r=row: self.update_difference(r, value))
            self.table.setCellWidget(row, 3, spin)
            self.spinboxes[row] = spin
            # Label de diferencia
            diff_label = QLabel("0")
            self.table.setCellWidget(row, 4, diff_label)
            self.difference_labels[row] = diff_label
            # Botón de ajuste individual
            adj_btn = QPushButton("Ajustar")
            adj_btn.clicked.connect(lambda checked, r=row: self.adjust_single(r))
            self.table.setCellWidget(row, 5, adj_btn)
            self.adjust_buttons[row] = adj_btn
            self.update_difference(row, spin.value())

    def update_difference(self, row, counted):
        """Actualiza la diferencia entre stock actual y cantidad contada."""
        expected = self.current_stock_data[row]["quantity"]
        diff = counted - expected
        self.difference_labels[row].setText(f"{diff:+d}")
        if diff != 0:
            self.difference_labels[row].setStyleSheet("color: red; font-weight: bold;")
        else:
            self.difference_labels[row].setStyleSheet("color: green;")

    def adjust_single(self, row):
        """Ajusta un solo producto."""
        stock = self.current_stock_data[row]
        counted = self.spinboxes[row].value()
        if counted == stock["quantity"]:
            QMessageBox.information(self, "Sin cambios", "La cantidad contada es igual al stock actual.")
            return
        # Pedir motivo
        reason, ok = QInputDialog.getText(self, "Motivo del ajuste", "Ingrese el motivo del ajuste:")
        if not ok or not reason.strip():
            return
        adjustment_type = "positive" if counted > stock["quantity"] else "negative"
        try:
            apply_adjustment(self.db, stock["batch_id"], self.location_combo.currentData(), counted, self.user.id, reason, adjustment_type)
            QMessageBox.information(self, "Éxito", "Ajuste aplicado correctamente.")
            self.load_inventory()  # recargar
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def apply_adjustments(self):
        """Aplica ajustes para todas las filas que tengan diferencia."""
        adjustments = []
        for row, stock in enumerate(self.current_stock_data):
            counted = self.spinboxes[row].value()
            if counted != stock["quantity"]:
                adjustments.append((row, stock, counted))
        if not adjustments:
            QMessageBox.information(self, "Sin ajustes", "No hay diferencias para ajustar.")
            return
        # Mostrar resumen
        msg = "Se aplicarán los siguientes ajustes:\n"
        for row, stock, counted in adjustments:
            product = self.db.query(Product).filter(Product.id == stock["product_id"]).first()
            diff = counted - stock["quantity"]
            msg += f"{product.name}: {stock['quantity']} -> {counted} ({diff:+d})\n"
        reply = QMessageBox.question(self, "Confirmar ajustes", msg + "\n¿Continuar?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        reason, ok = QInputDialog.getText(self, "Motivo global", "Ingrese el motivo de estos ajustes:")
        if not ok or not reason.strip():
            return
        try:
            for row, stock, counted in adjustments:
                adjustment_type = "positive" if counted > stock["quantity"] else "negative"
                apply_adjustment(self.db, stock["batch_id"], self.location_combo.currentData(), counted, self.user.id, reason, adjustment_type)
            QMessageBox.information(self, "Éxito", "Todos los ajustes aplicados.")
            self.load_inventory()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_count(self):
        """Guarda el conteo actual como historial (sin aplicar ajustes)."""
        items = []
        for row, stock in enumerate(self.current_stock_data):
            counted = self.spinboxes[row].value()
            items.append({
                "product_id": stock["product_id"],
                "batch_id": stock["batch_id"],
                "expected_quantity": stock["quantity"],
                "counted_quantity": counted,
                "difference": counted - stock["quantity"]
            })
        notes = "Conteo físico"
        try:
            save_inventory_count(self.db, self.location_combo.currentData(), self.user.id, items, notes)
            QMessageBox.information(self, "Guardado", "Conteo guardado en el historial.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# Necesitamos QInputDialog para pedir motivo
