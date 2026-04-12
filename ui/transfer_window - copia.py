# ui/transfer_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QMessageBox, QAbstractItemView, QCheckBox
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.stock_location import StockLocation
from models.transaction import Transaction

class TransferWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Transferencias al Piso")
        self.setStyleSheet("background-color: #F3F6FB;")

        main_layout = QVBoxLayout()

        # Tabla de productos disponibles
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Seleccionar", "Producto", "Cantidad disponible", "Cantidad a transferir"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        main_layout.addWidget(QLabel("Productos en almacén:"))
        main_layout.addWidget(self.table)

        # Botones
        button_layout = QHBoxLayout()
        self.transfer_btn = QPushButton("Transferir seleccionados")
        self.transfer_btn.setStyleSheet("background-color: #7BC8F6; border-radius: 5px; padding: 8px;")
        self.transfer_btn.clicked.connect(self.do_transfer)
        button_layout.addWidget(self.transfer_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Cargar datos al abrir la ventana
        self.load_products()

    def load_products(self):
        """Carga los productos que tienen stock en el almacén (location_id = 1)."""
        # Obtener el id de la ubicación Almacén (debe ser 1, pero lo buscamos por nombre)
        warehouse = self.db.query(StockLocation).filter(StockLocation.name == "Almacén").first()
        if not warehouse:
            QMessageBox.critical(self, "Error", "No se encontró la ubicación 'Almacén'.")
            return

        # Consultar stock en almacén, uniendo con lotes y productos
        results = (
            self.db.query(Stock, ProductBatch, Product)
            .join(ProductBatch, Stock.batch_id == ProductBatch.id)
            .join(Product, ProductBatch.product_id == Product.id)
            .filter(Stock.location_id == warehouse.id)
            .filter(Stock.quantity > 0)
            .all()
        )

        self.table.setRowCount(len(results))
        row = 0
        self.checkboxes = []   # lista de (checkbox, batch_id, product_name)
        self.spinboxes = {}    # diccionario (batch_id, row) -> spinbox

        for stock, batch, product in results:
            # Checkbox
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            self.checkboxes.append((checkbox, batch.id, product.name))

            # Nombre del producto
            item = QTableWidgetItem(product.name)
            self.table.setItem(row, 1, item)

            # Cantidad disponible (del stock)
            item = QTableWidgetItem(str(stock.quantity))
            self.table.setItem(row, 2, item)

            # Spinbox para cantidad a transferir
            spin = QSpinBox()
            spin.setRange(0, stock.quantity)
            spin.setValue(0)
            self.table.setCellWidget(row, 3, spin)
            self.spinboxes[(batch.id, row)] = spin

            row += 1

        if row == 0:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 4)
            self.table.setItem(0, 0, QTableWidgetItem("No hay productos en almacén"))

    def do_transfer(self):
        """Recoge las cantidades seleccionadas y realiza la transferencia."""
        items = []  # cada item: (batch_id, quantity)
        for checkbox, batch_id, product_name in self.checkboxes:
            if checkbox.isChecked():
                spin = self.spinboxes.get((batch_id, self.table.currentRow()))
                # Necesitamos encontrar el spin correspondiente a este batch_id.
                # Mejor recorremos el diccionario spinboxes.
                for (bid, row), spin in self.spinboxes.items():
                    if bid == batch_id:
                        qty = spin.value()
                        if qty > 0:
                            items.append((batch_id, qty, product_name))
                        break

        if not items:
            QMessageBox.information(self, "Sin selección", "No ha seleccionado productos o cantidades.")
            return

        # Confirmación
        msg = "¿Confirmar transferencia de los siguientes productos?\n\n"
        for batch_id, qty, prod_name in items:
            msg += f"- {prod_name}: {qty} unidades\n"
        reply = QMessageBox.question(self, "Confirmar transferencia", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            # Realizar la transferencia
            self.transfer_batches(items)
            QMessageBox.information(self, "Éxito", "Transferencia realizada correctamente.")
            self.load_products()  # recargar la tabla
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al transferir: {str(e)}")

    def transfer_batches(self, items):
        """items = lista de (batch_id, quantity, product_name)"""
        warehouse = self.db.query(StockLocation).filter(StockLocation.name == "Almacén").first()
        sales_floor = self.db.query(StockLocation).filter(StockLocation.name == "Piso").first()
        if not warehouse or not sales_floor:
            raise Exception("Ubicaciones no encontradas")

        for batch_id, qty, _ in items:
            # Obtener el lote
            batch = self.db.query(ProductBatch).filter(ProductBatch.id == batch_id).first()
            if not batch:
                raise Exception(f"Lote {batch_id} no encontrado")

            # Verificar stock en almacén
            stock_warehouse = self.db.query(Stock).filter(
                Stock.batch_id == batch_id,
                Stock.location_id == warehouse.id
            ).first()
            if not stock_warehouse or stock_warehouse.quantity < qty:
                raise Exception(f"Stock insuficiente para el lote {batch_id}")

            # Descontar del almacén
            stock_warehouse.quantity -= qty

            # Actualizar stock en piso
            stock_floor = self.db.query(Stock).filter(
                Stock.batch_id == batch_id,
                Stock.location_id == sales_floor.id
            ).first()
            if stock_floor:
                stock_floor.quantity += qty
            else:
                stock_floor = Stock(batch_id=batch_id, location_id=sales_floor.id, quantity=qty)
                self.db.add(stock_floor)

            # Registrar transacción
            transaction = Transaction(
                type="transfer",
                from_location_id=warehouse.id,
                to_location_id=sales_floor.id,
                batch_id=batch_id,
                quantity=qty,
                user_id=self.user.id,
                notes=f"Transferencia de {qty} unidades del lote {batch_id}"
            )
            self.db.add(transaction)

        self.db.commit()