# ui/special_products_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QSpinBox, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer
from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.stock_location import StockLocation
from services.product_service import register_sale
from datetime import datetime, date
from sqlalchemy import func
from models.sale import Sale

class SpecialProductsWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Productos Especiales")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #F5F7FA;")
        
        self.cart = []  # carrito para especiales
        
        # Layout principal con dos paneles (similar al POS)
        main_layout = QHBoxLayout()
        
        # Panel izquierdo: lista de productos especiales disponibles
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar producto especial...")
        self.search_input.textChanged.connect(self.filter_products)
        left_layout.addWidget(self.search_input)
        
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(4)
        self.products_table.setHorizontalHeaderLabels(["Código", "Nombre", "Precio", "Stock"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.doubleClicked.connect(self.add_to_cart)
        left_layout.addWidget(self.products_table)
        
        add_btn = QPushButton("➕ Agregar al carrito")
        add_btn.clicked.connect(self.add_selected)
        left_layout.addWidget(add_btn)
        
        # Panel derecho: carrito y totales
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("🛒 Carrito de especiales"))
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(4)
        self.cart_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio", "Subtotal"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.cart_table)
        
        self.total_label = QLabel("Total: 0.00 CUP")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.total_label)
        
        self.pay_btn = QPushButton("💰 Pagar venta especial")
        self.pay_btn.setStyleSheet("background-color: #4A90E2; border-radius: 8px; padding: 10px;")
        self.pay_btn.clicked.connect(self.process_payment)
        right_layout.addWidget(self.pay_btn)
        
        # Reporte de ventas de especiales
        report_group = QWidget()
        report_layout = QVBoxLayout(report_group)
        report_layout.addWidget(QLabel("📊 Ventas de especiales"))
        self.daily_label = QLabel("Ventas hoy: 0.00 CUP")
        self.monthly_label = QLabel("Ventas mes: 0.00 CUP")
        report_layout.addWidget(self.daily_label)
        report_layout.addWidget(self.monthly_label)
        right_layout.addWidget(report_group)
        
        main_layout.addWidget(left_widget, 2)  # más ancho
        main_layout.addWidget(right_widget, 1)
        self.setLayout(main_layout)
        
        # Cargar datos
        self.all_special_products = []
        self.load_special_products()
        self.update_sales_summary()
    
    def load_special_products(self):
        """Carga todos los productos especiales que tienen stock en la ubicación 'Especiales'."""
        special_loc = self.db.query(StockLocation).filter(StockLocation.name == "Especiales").first()
        if not special_loc:
            QMessageBox.critical(self, "Error", "Ubicación 'Especiales' no encontrada.")
            return
        results = (
            self.db.query(Stock, ProductBatch, Product)
            .join(ProductBatch, Stock.batch_id == ProductBatch.id)
            .join(Product, ProductBatch.product_id == Product.id)
            .filter(Stock.location_id == special_loc.id)
            .filter(Stock.quantity > 0)
            .filter(Product.is_special == True)
            .all()
        )
        self.all_special_products = []
        for stock, batch, product in results:
            self.all_special_products.append({
                "stock_id": stock.id,
                "batch_id": batch.id,
                "code": product.code,
                "name": product.name,
                "price": batch.sale_price,
                "quantity": stock.quantity
            })
        self.filter_products()
    
    def filter_products(self):
        search = self.search_input.text().strip().lower()
        filtered = [p for p in self.all_special_products if search in p["name"].lower() or search in p["code"].lower()]
        self.update_products_table(filtered)
    
    def update_products_table(self, products):
        self.products_table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.products_table.setItem(row, 0, QTableWidgetItem(p["code"]))
            self.products_table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.products_table.setItem(row, 2, QTableWidgetItem(f"{p['price']:.2f}"))
            self.products_table.setItem(row, 3, QTableWidgetItem(str(p["quantity"])))
    
    def add_selected(self):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un producto.")
            return
        # Necesitamos obtener el producto de la lista filtrada. Usamos el código como clave.
        code = self.products_table.item(row, 0).text()
        product_data = next((p for p in self.all_special_products if p["code"] == code), None)
        if product_data:
            self.add_to_cart_dialog(product_data)
    
    def add_to_cart(self, index):
        self.add_selected()
    
    def add_to_cart_dialog(self, product_data):
        available = product_data["quantity"]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Agregar {product_data['name']}")
        layout = QFormLayout()
        spin = QSpinBox()
        spin.setRange(1, available)
        spin.setValue(1)
        layout.addRow("Cantidad:", spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            qty = spin.value()
            # Verificar si ya existe en carrito (mismo batch)
            for item in self.cart:
                if item["batch_id"] == product_data["batch_id"]:
                    item["quantity"] += qty
                    item["subtotal"] = item["quantity"] * item["price"]
                    self.update_cart_table()
                    self.update_total()
                    return
            self.cart.append({
                "product_name": product_data["name"],
                "batch_id": product_data["batch_id"],
                "quantity": qty,
                "price": product_data["price"],
                "subtotal": qty * product_data["price"],
                "code": product_data["code"]
            })
            self.update_cart_table()
            self.update_total()
    
    def update_cart_table(self):
        self.cart_table.setRowCount(len(self.cart))
        for row, item in enumerate(self.cart):
            self.cart_table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.cart_table.setItem(row, 1, QTableWidgetItem(str(item["quantity"])))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{item['price']:.2f}"))
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"{item['subtotal']:.2f}"))
            # Botón eliminar
            del_btn = QPushButton("❌")
            del_btn.clicked.connect(lambda checked, r=row: self.remove_from_cart(r))
            self.cart_table.setCellWidget(row, 4, del_btn)
    
    def remove_from_cart(self, row):
        del self.cart[row]
        self.update_cart_table()
        self.update_total()
    
    def update_total(self):
        total = sum(item["subtotal"] for item in self.cart)
        self.total_label.setText(f"Total: {total:.2f} CUP")
    
    def process_payment(self):
        if not self.cart:
            QMessageBox.information(self, "Carrito vacío", "No hay productos especiales en el carrito.")
            return
        total = sum(item["subtotal"] for item in self.cart)
        # Diálogo de pago simplificado (igual que POS)
        dialog = QDialog(self)
        dialog.setWindowTitle("Pago especial")
        layout = QVBoxLayout()
        form = QFormLayout()
        method_combo = QComboBox()
        method_combo.addItems(["Efectivo", "Zelle", "Transferencia"])
        form.addRow("Método de pago:", method_combo)
        cash_received = QDoubleSpinBox()
        cash_received.setRange(0, 1000000)
        cash_received.setValue(total)
        cash_received.setPrefix("Recibido: ")
        cash_received.setSuffix(" CUP")
        cash_received.setVisible(False)
        def toggle_visible(index):
            cash_received.setVisible(method_combo.currentText() == "Efectivo")
        method_combo.currentIndexChanged.connect(toggle_visible)
        toggle_visible(0)
        form.addRow(cash_received)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        if dialog.exec() != QDialog.Accepted:
            return
        payment_method = method_combo.currentText()
        change = 0.0
        if payment_method == "Efectivo":
            received = cash_received.value()
            if received < total:
                QMessageBox.warning(self, "Pago insuficiente", f"El cliente entregó {received} CUP, total {total} CUP.")
                return
            change = received - total
            QMessageBox.information(self, "Vuelto", f"Vuelto: {change:.2f} CUP")
        # Confirmar
        reply = QMessageBox.question(self, "Confirmar venta especial", f"Total: {total:.2f} CUP\nMétodo: {payment_method}\n¿Confirmar?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            items_for_sale = []
            for item in self.cart:
                items_for_sale.append({
                    "batch_id": item["batch_id"],
                    "quantity": item["quantity"],
                    "price": item["price"]
                })
            # Reutilizamos la misma función register_sale (funciona porque la ubicación es la de especiales)
            sale_id = register_sale(
                db=self.db,
                items=items_for_sale,
                payment_method=payment_method,
                total=total,
                change_given=change,
                user_id=self.user.id
            )
            QMessageBox.information(self, "Venta especial exitosa", f"Venta registrada con ID {sale_id}")
            self.print_receipt(sale_id, total, payment_method, change)
            self.cart.clear()
            self.update_cart_table()
            self.update_total()
            self.load_special_products()  # recargar stock
            self.update_sales_summary()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta: {str(e)}")
    
    def print_receipt(self, sale_id, total, method, change):
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            receipt = f"""
=== TIQUE DE VENTA ESPECIAL ===
Fecha: {now}
Venta #: {sale_id}
Atendido por: {self.user.username}
------------------------
"""
            for item in self.cart:
                receipt += f"{item['product_name']} x{item['quantity']} = {item['subtotal']:.2f} CUP\n"
            receipt += f"------------------------\nTotal: {total:.2f} CUP\nMétodo: {method}\n"
            if method == "Efectivo":
                receipt += f"Vuelto: {change:.2f} CUP\n"
            receipt += "¡Gracias por su compra!\n"
            filename = f"receipt_special_{sale_id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(receipt)
            QMessageBox.information(self, "Tique", f"Tique guardado en {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Error al imprimir", str(e))
    
    def update_sales_summary(self):
        # Ventas de productos especiales: sumar total de ventas donde los productos vendidos sean especiales
        # Esto requiere una consulta más compleja. Por simplicidad, mostraremos solo las ventas registradas en la tabla Sale
        # pero filtradas por transacciones que involucren lotes de productos especiales.
        # Para no complicar, asumimos que todas las ventas desde esta ventana son especiales,
        # pero como usamos la misma tabla Sale, podemos filtrar por fecha y luego calcular aparte.
        # Lo dejamos como está por ahora, pero se puede mejorar.
        today = date.today()
        first_day_month = date(today.year, today.month, 1)
        daily_total = self.db.query(func.sum(Sale.total)).filter(Sale.created_at >= today).scalar() or 0.0
        monthly_total = self.db.query(func.sum(Sale.total)).filter(Sale.created_at >= first_day_month).scalar() or 0.0
        self.daily_label.setText(f"Ventas especiales hoy: {daily_total:.2f} CUP")
        self.monthly_label.setText(f"Ventas especiales mes: {monthly_total:.2f} CUP")