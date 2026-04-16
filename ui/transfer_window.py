# ui/transfer_window.py - Transferencias con buscador y lista de agregados
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QSpinBox, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.stock_location import StockLocation
from services.product_service import transfer_products
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout
from sqlalchemy import func

class TransferWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Transferencias al Piso")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("background-color: #F5F7FA;")
        
        # Lista de productos pendientes de transferir
        self.transfer_list = []  # cada item: {"batch_id": int, "product_name": str, "quantity": int}
        
        layout = QVBoxLayout()
        
        # ========== SECCIÓN DE BÚSQUEDA ==========
        search_group = QGroupBox("Buscar producto en almacén")
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre o código del producto...")
        self.search_btn = QPushButton("Buscar")
        self.search_btn.clicked.connect(self.search_products)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Tabla de resultados de búsqueda
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Producto", "Código", "Stock disponible", "Agregar"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(QLabel("Productos encontrados:"))
        layout.addWidget(self.results_table)
        
        # ========== LISTA DE PRODUCTOS A TRANSFERIR ==========
        layout.addWidget(QLabel("Productos a transferir:"))
        self.transfer_table = QTableWidget()
        self.transfer_table.setColumnCount(4)
        self.transfer_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Stock disponible", "Eliminar"])
        self.transfer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transfer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.transfer_table)
        
        # ========== BOTONES DE ACCIÓN ==========
        btn_layout = QHBoxLayout()
        self.finalize_btn = QPushButton("✅ Finalizar transferencia")
        self.finalize_btn.setStyleSheet("background-color: #4A90E2; border-radius: 8px; padding: 10px;")
        self.finalize_btn.clicked.connect(self.finalize_transfer)
        self.clear_btn = QPushButton("🗑️ Limpiar lista")
        self.clear_btn.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.finalize_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Al iniciar, cargar productos por defecto (opcional)
        self.search_products()
    
    def search_products(self):
        """Busca productos en el almacén según el texto ingresado."""
        search_text = self.search_input.text().strip().lower()
        # Obtener ubicación Almacén
        warehouse = self.db.query(StockLocation).filter(StockLocation.name == "Almacén").first()
        if not warehouse:
            QMessageBox.critical(self, "Error", "No se encontró la ubicación 'Almacén'.")
            return
        
        # Consultar stock en almacén, agrupado por producto (sumando cantidades de lotes)
        query = (
            self.db.query(Product, func.sum(Stock.quantity))
            .join(ProductBatch, Product.id == ProductBatch.product_id)
            .join(Stock, Stock.batch_id == ProductBatch.id)
            .filter(Stock.location_id == warehouse.id)
            .filter(Stock.quantity > 0)
            .group_by(Product.id)
        )
        if search_text:
            query = query.filter(Product.name.contains(search_text) | Product.code.contains(search_text))
        
        results = query.all()
        
        self.results_table.setRowCount(len(results))
        self.row_data = {}  # guardar batch_ids disponibles (para luego agregar)
        for row, (product, total_qty) in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(product.name))
            self.results_table.setItem(row, 1, QTableWidgetItem(product.code))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(total_qty)))
            
            # Botón "Agregar"
            add_btn = QPushButton("➕ Agregar")
            add_btn.clicked.connect(lambda checked, p=product, q=total_qty: self.add_to_list(p, q))
            self.results_table.setCellWidget(row, 3, add_btn)
    
    def add_to_list(self, product, available_qty):
        """Abre un diálogo para ingresar cantidad y agrega el producto a la lista de transferencia."""
        # Verificar si ya existe en la lista
        for item in self.transfer_list:
            if item["product_id"] == product.id:
                QMessageBox.warning(self, "Producto duplicado", "El producto ya está en la lista. Edite la cantidad directamente en la tabla.")
                return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Transferir {product.name}")
        layout = QFormLayout()
        spin = QSpinBox()
        spin.setRange(1, available_qty)
        spin.setValue(1)
        layout.addRow("Cantidad:", spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            qty = spin.value()
            self.transfer_list.append({
                "product_id": product.id,
                "product_name": product.name,
                "quantity": qty,
                "available": available_qty
            })
            self.update_transfer_table()
    
    def update_transfer_table(self):
        """Actualiza la tabla de productos a transferir."""
        self.transfer_table.setRowCount(len(self.transfer_list))
        for row, item in enumerate(self.transfer_list):
            self.transfer_table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            # Spinbox para editar cantidad
            spin = QSpinBox()
            spin.setRange(1, item["available"])
            spin.setValue(item["quantity"])
            spin.valueChanged.connect(lambda value, r=row: self.update_quantity(r, value))
            self.transfer_table.setCellWidget(row, 1, spin)
            self.transfer_table.setItem(row, 2, QTableWidgetItem(str(item["available"])))
            # Botón eliminar
            del_btn = QPushButton("❌")
            del_btn.clicked.connect(lambda checked, r=row: self.remove_from_list(r))
            self.transfer_table.setCellWidget(row, 3, del_btn)
    
    def update_quantity(self, row, new_qty):
        self.transfer_list[row]["quantity"] = new_qty
    
    def remove_from_list(self, row):
        del self.transfer_list[row]
        self.update_transfer_table()
    
    def clear_list(self):
        self.transfer_list.clear()
        self.update_transfer_table()
    
    def finalize_transfer(self):
        if not self.transfer_list:
            QMessageBox.information(self, "Lista vacía", "No hay productos para transferir.")
            return
        
        # Mostrar resumen
        msg = "¿Confirmar transferencia de los siguientes productos?\n\n"
        for item in self.transfer_list:
            msg += f"- {item['product_name']}: {item['quantity']} unidades\n"
        reply = QMessageBox.question(self, "Confirmar transferencia", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Llamar a la función de transferencia (necesita lista de (product_id, quantity, user_id))
            items = [(item["product_id"], item["quantity"], self.user.id) for item in self.transfer_list]
            transfer_products(self.db, items, self.user.id)
            QMessageBox.information(self, "Éxito", "Transferencia realizada correctamente.")
            self.clear_list()
            self.search_products()  # refrescar resultados de búsqueda
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo realizar la transferencia:\n{str(e)}")