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
        self.setStyleSheet("background-color: #F5F7FA;")

        main_layout = QVBoxLayout()

        # Botón Actualizar
        top_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Actualizar")
        self.refresh_btn.clicked.connect(self.load_products)
        top_layout.addStretch()
        top_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(top_layout)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Seleccionar", "Producto", "Cantidad disponible", "Cantidad a transferir"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        main_layout.addWidget(QLabel("Productos en almacén:"))
        main_layout.addWidget(self.table)

        self.transfer_btn = QPushButton("Transferir seleccionados")
        self.transfer_btn.clicked.connect(self.do_transfer)
        main_layout.addWidget(self.transfer_btn)

        self.setLayout(main_layout)

        self.checkboxes = []
        self.spinboxes = {}
        self.load_products()

    def load_products(self):
        """Carga productos directamente de product_batches con quantity_remaining > 0."""
        print("=== load_products() ===")
        self.checkboxes.clear()
        self.spinboxes.clear()

        batches = self.db.query(ProductBatch).filter(ProductBatch.quantity_remaining > 0).all()
        print(f"DEBUG: batches encontrados = {len(batches)}")

        if not batches:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 4)
            self.table.setItem(0, 0, QTableWidgetItem("No hay productos en almacén"))
            return

        self.table.setRowCount(len(batches))
        row = 0
        for batch in batches:
            product = self.db.query(Product).filter(Product.id == batch.product_id).first()
            if not product:
                continue
            print(f"DEBUG: Producto {product.name}, cantidad {batch.quantity_remaining}")

            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            self.checkboxes.append((checkbox, batch.id, product.name))

            self.table.setItem(row, 1, QTableWidgetItem(product.name))
            self.table.setItem(row, 2, QTableWidgetItem(str(batch.quantity_remaining)))
            spin = QSpinBox()
            spin.setRange(0, batch.quantity_remaining)
            spin.setValue(0)
            self.table.setCellWidget(row, 3, spin)
            self.spinboxes[(batch.id, row)] = spin
            row += 1

    def do_transfer(self):
        items = []
        for checkbox, batch_id, prod_name in self.checkboxes:
            if checkbox.isChecked():
                spin = None
                for (bid, row), s in self.spinboxes.items():
                    if bid == batch_id:
                        spin = s
                        break
                if spin and spin.value() > 0:
                    items.append((batch_id, spin.value(), prod_name))
        if not items:
            QMessageBox.information(self, "Sin selección", "No ha seleccionado productos o cantidades.")
            return
        msg = "Confirmar transferencia:\n" + "\n".join(f"- {name}: {qty}" for _, qty, name in items)
        reply = QMessageBox.question(self, "Confirmar", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.transfer_batches(items)
            QMessageBox.information(self, "Éxito", "Transferencia realizada")
            self.load_products()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def transfer_batches(self, items):
        """Transfiere lotes: descuenta de quantity_remaining y actualiza stock en piso."""
        warehouse = self.db.query(StockLocation).filter(StockLocation.name.ilike("%almacen%")).first()
        piso = self.db.query(StockLocation).filter(StockLocation.name == "Piso").first()
        if not warehouse or not piso:
            raise Exception("Ubicaciones no encontradas")

        for batch_id, qty, _ in items:
            batch = self.db.query(ProductBatch).filter(ProductBatch.id == batch_id).first()
            if not batch or batch.quantity_remaining < qty:
                raise Exception(f"Stock insuficiente para lote {batch_id}")
            batch.quantity_remaining -= qty

            stock_wh = self.db.query(Stock).filter(
                Stock.batch_id == batch_id,
                Stock.location_id == warehouse.id
            ).first()
            if stock_wh:
                stock_wh.quantity -= qty
            else:
                stock_wh = Stock(batch_id=batch_id, location_id=warehouse.id, quantity=-qty)
                self.db.add(stock_wh)

            stock_floor = self.db.query(Stock).filter(
                Stock.batch_id == batch_id,
                Stock.location_id == piso.id
            ).first()
            if stock_floor:
                stock_floor.quantity += qty
            else:
                stock_floor = Stock(batch_id=batch_id, location_id=piso.id, quantity=qty)
                self.db.add(stock_floor)

            trans = Transaction(
                type="transfer",
                batch_id=batch_id,
                quantity=qty,
                total=0.0,
                user_id=self.user.id
            )
            self.db.add(trans)

        self.db.commit()