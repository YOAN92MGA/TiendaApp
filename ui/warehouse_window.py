# ui/warehouse_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from datetime import date, timedelta

class WarehouseWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Inventario en Almacen")
        self.setStyleSheet("background-color: #F3F6FB;")

        main_layout = QVBoxLayout()

        # Panel superior con tipo de cambio
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Tipo de cambio USD actual (CUP/USD):"))
        self.usd_rate_input = QLineEdit()
        self.usd_rate_input.setPlaceholderText("Ej: 24.00")
        self.usd_rate_input.setFixedWidth(100)
        self.refresh_btn = QPushButton("Actualizar")
        self.refresh_btn.setStyleSheet("background-color: #AEDFF7; border-radius: 5px;")
        self.refresh_btn.clicked.connect(self.load_data)
        rate_layout.addWidget(self.usd_rate_input)
        rate_layout.addWidget(self.refresh_btn)
        rate_layout.addStretch()
        main_layout.addLayout(rate_layout)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(7)  # Reducimos columnas (quitamos proveedor para simplificar)
        self.table.setHorizontalHeaderLabels([
            "Producto", "Categorea", "Cantidad", "Precio Compra (CUP)",
            "Precio Venta", "Margen", "Vencimiento"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        main_layout.addWidget(self.table)

        self.setLayout(main_layout)
        self.load_data()

    def load_data(self):
        # Obtener tipo de cambio (si no hay, usar 1)
        usd_rate_text = self.usd_rate_input.text()
        if usd_rate_text:
            try:
                current_usd_rate = float(usd_rate_text)
            except ValueError:
                QMessageBox.warning(self, "Error", "Tipo de cambio invalido. Se usara 1.0")
                current_usd_rate = 1.0
        else:
            current_usd_rate = 1.0

        # Obtener todos los lotes con cantidad restante > 0
        batches = self.db.query(ProductBatch).filter(ProductBatch.quantity_remaining > 0).all()

        self.table.setRowCount(0)
        row = 0
        today = date.today()
        threshold_date = today + timedelta(days=15)

        for batch in batches:
            # Obtener el producto asociado
            product = self.db.query(Product).filter(Product.id == batch.product_id).first()
            if not product:
                continue

            # Calcular margen con el tipo de cambio actual (no se usa realmente para el margen, pero lo dejamos)
            # El margen se calcula sobre precio venta vs precio compra en CUP
            gain = batch.sale_price - batch.purchase_price_cup
            margin = (gain / batch.purchase_price_cup) * 100 if batch.purchase_price_cup > 0 else 0

            row_color = None
            if margin < 30:
                row_color = QColor(255, 200, 200)
            if batch.expiration_date <= threshold_date:
                row_color = QColor(255, 200, 200)

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(product.name))
            self.table.setItem(row, 1, QTableWidgetItem(product.category))
            self.table.setItem(row, 2, QTableWidgetItem(str(batch.quantity_remaining)))
            self.table.setItem(row, 3, QTableWidgetItem(f"{batch.purchase_price_cup:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{batch.sale_price:.2f}"))
            margin_text = f"{margin:.1f}%"
            item_margin = QTableWidgetItem(margin_text)
            if row_color:
                item_margin.setBackground(row_color)
            self.table.setItem(row, 5, item_margin)
            exp_date = batch.expiration_date.strftime("%d/%m/%Y")
            item_exp = QTableWidgetItem(exp_date)
            if row_color:
                item_exp.setBackground(row_color)
            self.table.setItem(row, 6, item_exp)
            row += 1

        if row == 0:
            self.table.setRowCount(1)
            empty_item = QTableWidgetItem("No hay productos en almacen")
            self.table.setSpan(0, 0, 1, 7)
            self.table.setItem(0, 0, empty_item)