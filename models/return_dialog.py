# ui/return_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QSpinBox, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from models.sale import Sale
from models.sale_item import SaleItem
from models.batch import ProductBatch
from models.product import Product
from models.stock import Stock
from models.stock_location import StockLocation
from models.transaction import Transaction
from utils.security import verify_password

class ReturnDialog(QDialog):
    def __init__(self, db: Session, current_user, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_user = current_user
        self.setWindowTitle("Devolución de productos")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Buscar venta por ID
        search_layout = QHBoxLayout()
        self.sale_id_input = QLineEdit()
        self.sale_id_input.setPlaceholderText("Número de venta")
        self.search_btn = QPushButton("Buscar venta")
        self.search_btn.clicked.connect(self.search_sale)
        search_layout.addWidget(QLabel("Venta ID:"))
        search_layout.addWidget(self.sale_id_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Información de la venta
        self.sale_info_label = QLabel("")
        layout.addWidget(self.sale_info_label)
        
        # Tabla de productos de la venta
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["Producto", "Cantidad vendida", "Cantidad a devolver", "Precio unit.", "Subtotal a devolver"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.products_table)
        
        # Botón para solicitar contraseña y procesar
        self.return_btn = QPushButton("Autorizar y procesar devolución")
        self.return_btn.setEnabled(False)
        self.return_btn.clicked.connect(self.ask_password_and_return)
        layout.addWidget(self.return_btn)
        
        self.setLayout(layout)
        self.sale = None
        self.sale_items = []
        self.spins = []
    
    def search_sale(self):
        try:
            sale_id = int(self.sale_id_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingrese un número de venta válido.")
            return
        self.sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
        if not self.sale:
            QMessageBox.warning(self, "No encontrada", f"Venta #{sale_id} no existe.")
            return
        self.sale_info_label.setText(f"Venta #{self.sale.id} - {self.sale.created_at.strftime('%Y-%m-%d %H:%M')} - Total: {self.sale.total:.2f} CUP")
        self.load_sale_items()
    
    def load_sale_items(self):
        self.sale_items = self.db.query(SaleItem).filter(SaleItem.sale_id == self.sale.id).all()
        self.products_table.setRowCount(len(self.sale_items))
        self.spins = []
        for row, item in enumerate(self.sale_items):
            batch = self.db.query(ProductBatch).filter(ProductBatch.id == item.batch_id).first()
            product = self.db.query(Product).filter(Product.id == batch.product_id).first() if batch else None
            product_name = product.name if product else "Desconocido"
            self.products_table.setItem(row, 0, QTableWidgetItem(product_name))
            self.products_table.setItem(row, 1, QTableWidgetItem(str(item.quantity)))
            spin = QSpinBox()
            spin.setRange(0, item.quantity)
            spin.setValue(0)
            spin.valueChanged.connect(lambda: self.update_total())
            self.products_table.setCellWidget(row, 2, spin)
            self.spins.append(spin)
            self.products_table.setItem(row, 3, QTableWidgetItem(f"{item.price:.2f}"))
            self.products_table.setItem(row, 4, QTableWidgetItem("0.00"))
        self.return_btn.setEnabled(True)
        self.update_total()
    
    def update_total(self):
        total_return = 0.0
        for row, item in enumerate(self.sale_items):
            qty = self.spins[row].value()
            price = item.price
            subtotal = qty * price
            self.products_table.setItem(row, 4, QTableWidgetItem(f"{subtotal:.2f}"))
            total_return += subtotal
        self.return_btn.setText(f"Autorizar devolución (Total a reembolsar: {total_return:.2f} CUP)")
    
    def ask_password_and_return(self):
        # Verificar que haya al menos un producto con cantidad > 0
        if all(spin.value() == 0 for spin in self.spins):
            QMessageBox.warning(self, "Sin devolución", "No ha seleccionado ningún producto para devolver.")
            return
        
        # Solicitar contraseña de administrador
        password, ok = QInputDialog.getText(self, "Autorización requerida", 
                                            "Contraseña de administrador:", QLineEdit.Password)
        if not ok or not password:
            return
        # Verificar que el usuario actual sea admin o que la contraseña coincida con algún admin
        admin = self.db.query(User).filter(User.role == "admin", User.password == hash_password(password)).first()
        if not admin:
            QMessageBox.warning(self, "Acceso denegado", "Contraseña incorrecta o no tiene permisos de administrador.")
            return
        
        # Procesar devolución
        try:
            self.process_return(admin.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def process_return(self, admin_id):
        # Obtener ubicación piso
        piso = self.db.query(StockLocation).filter(StockLocation.name == "Piso").first()
        if not piso:
            raise Exception("Ubicación 'Piso' no encontrada")
        
        for row, item in enumerate(self.sale_items):
            qty = self.spins[row].value()
            if qty == 0:
                continue
            # Devolver stock al piso
            stock = self.db.query(Stock).filter(
                Stock.batch_id == item.batch_id,
                Stock.location_id == piso.id
            ).first()
            if stock:
                stock.quantity += qty
            else:
                stock = Stock(batch_id=item.batch_id, location_id=piso.id, quantity=qty)
                self.db.add(stock)
            
            # Registrar transacción de devolución
            trans = Transaction(
                type="return",
                to_location_id=piso.id,
                batch_id=item.batch_id,
                quantity=qty,
                user_id=admin_id,
                notes=f"Devolución de venta #{self.sale.id}"
            )
            self.db.add(trans)
        
        self.db.commit()
        QMessageBox.information(self, "Éxito", "Devolución procesada correctamente.")
        self.accept()