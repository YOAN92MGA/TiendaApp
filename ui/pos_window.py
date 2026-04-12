# ui/pos_window.py - Punto de Venta mejorado con impresión térmica
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QSpinBox, QDialog, QDialogButtonBox,
    QFormLayout, QComboBox, QDoubleSpinBox, QSplitter,
)
from PySide6.QtWidgets import QTextEdit, QDialogButtonBox

from PySide6.QtGui import QKeySequence, QColor, QBrush, QShortcut
from PySide6.QtCore import Qt, QEvent
from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.stock_location import StockLocation
from services.product_service import register_sale
from datetime import datetime, date
from sqlalchemy import func
from models.sale import Sale
import tempfile
import os
import subprocess
from services.company_service import get_company_settings

try:
    import win32print
    WIN32_PRINT_AVAILABLE = True
except ImportError:
    WIN32_PRINT_AVAILABLE = False

class POSWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Punto de Venta")
        self.setStyleSheet("background-color: #F5F7FA;")
        
        self.cart = []
        
        main_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo: productos
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por nombre o código... (F2)")
        self.search_input.textChanged.connect(self.filter_products)
        left_layout.addWidget(self.search_input)
        
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels(["Código", "Producto", "Precio", "Stock", "Categoría", ""])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.doubleClicked.connect(self.add_selected_product)
        left_layout.addWidget(self.products_table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Agregar seleccionado (Enter)")
        add_btn.clicked.connect(self.add_selected_product)
        refresh_btn = QPushButton("🔄 Refrescar (F5)")
        refresh_btn.clicked.connect(self.load_all_products)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(refresh_btn)
        left_layout.addLayout(btn_layout)
        
        # Panel derecho: carrito
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        cart_header = QHBoxLayout()
        cart_header.addWidget(QLabel("🛒 Carrito de compras"))
        self.item_count_label = QLabel("0 items | 0 unidades")
        self.item_count_label.setStyleSheet("color: #555;")
        cart_header.addStretch()
        cart_header.addWidget(self.item_count_label)
        right_layout.addLayout(cart_header)
        
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio Unit.", "Subtotal", "Eliminar", "Editar"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        right_layout.addWidget(self.cart_table)
        
        total_layout = QHBoxLayout()
        self.total_label = QLabel("Total: 0.00 CUP")
        self.total_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        total_layout.addStretch()
        total_layout.addWidget(self.total_label)
        total_layout.addStretch()
        right_layout.addLayout(total_layout)
        
        action_layout = QHBoxLayout()
        self.clear_cart_btn = QPushButton("🗑️ Limpiar carrito (Ctrl+Q)")
        self.clear_cart_btn.clicked.connect(self.clear_cart)
        self.pay_btn = QPushButton("💰 Pagar (Ctrl+P)")
        self.pay_btn.setStyleSheet("background-color: #4A90E2; border-radius: 8px; padding: 12px; font-size: 14px;")
        self.pay_btn.clicked.connect(self.process_payment)
        action_layout.addWidget(self.clear_cart_btn)
        action_layout.addWidget(self.pay_btn)
        right_layout.addLayout(action_layout)
        
        summary_layout = QHBoxLayout()
        self.daily_label = QLabel("Ventas hoy: 0.00 CUP")
        self.monthly_label = QLabel("Ventas mes: 0.00 CUP")
        summary_layout.addWidget(self.daily_label)
        summary_layout.addWidget(self.monthly_label)
        right_layout.addLayout(summary_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        # Atajos de teclado
        QShortcut(QKeySequence("F2"), self).activated.connect(self.search_input.setFocus)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.load_all_products)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.clear_cart)
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.process_payment)
        self.products_table.installEventFilter(self)
        
        self.all_products = []
        self.load_all_products()
        self.filter_products()
        self.update_sales_summary()
    
    def eventFilter(self, obj, event):
        if obj == self.products_table and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.add_selected_product()
                return True
        return super().eventFilter(obj, event)
    def show_receipt_dialog(self, receipt_text):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ticket de venta")
        dialog.setMinimumSize(400, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Área de texto para mostrar el ticket
        text_edit = QTextEdit()
        text_edit.setPlainText(receipt_text)
        text_edit.setReadOnly(True)
        text_edit.setFontFamily("monospace")
        layout.addWidget(text_edit)
        
        # Botones
        button_box = QDialogButtonBox()
        print_btn = button_box.addButton("Imprimir", QDialogButtonBox.AcceptRole)
        close_btn = button_box.addButton("Cerrar", QDialogButtonBox.RejectRole)
        button_box.accepted.connect(lambda: self.print_receipt(receipt_text) or dialog.accept())
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    def load_all_products(self):
        piso = self.db.query(StockLocation).filter(StockLocation.name == "Piso").first()
        if not piso:
            QMessageBox.critical(self, "Error", "No se encontró la ubicación 'Piso'.")
            return
        results = (
            self.db.query(Stock, ProductBatch, Product)
            .join(ProductBatch, Stock.batch_id == ProductBatch.id)
            .join(Product, ProductBatch.product_id == Product.id)
            .filter(Stock.location_id == piso.id, Stock.quantity > 0)
            .all()
        )
        self.all_products = []
        for stock, batch, product in results:
            self.all_products.append({
                "stock_id": stock.id,
                "batch_id": batch.id,
                "product_id": product.id,
                "code": product.code,
                "name": product.name,
                "price": batch.sale_price,
                "quantity": stock.quantity,
                "category": product.category
            })
        self.filter_products()
    
    def filter_products(self):
        search = self.search_input.text().strip().lower()
        filtered = [p for p in self.all_products if search in p["name"].lower() or search in p["code"].lower()]
        self.update_products_table(filtered)
    
    def update_products_table(self, products):
        self.products_table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.products_table.setItem(row, 0, QTableWidgetItem(p["code"]))
            self.products_table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.products_table.setItem(row, 2, QTableWidgetItem(f"{p['price']:.2f}"))
            stock_item = QTableWidgetItem(str(p["quantity"]))
            if p["quantity"] < 5:
                stock_item.setBackground(QBrush(QColor(255, 255, 150)))
            self.products_table.setItem(row, 3, stock_item)
            self.products_table.setItem(row, 4, QTableWidgetItem(p["category"]))
            self.products_table.setItem(row, 5, QTableWidgetItem(""))
    
    def add_selected_product(self):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un producto de la lista.")
            return
        code = self.products_table.item(row, 0).text()
        product = next((p for p in self.all_products if p["code"] == code), None)
        if product:
            self.show_quantity_dialog(product)
    
    def show_quantity_dialog(self, product):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Agregar {product['name']}")
        layout = QFormLayout()
        spin = QSpinBox()
        spin.setRange(1, product["quantity"])
        spin.setValue(1)
        spin.selectAll()
        layout.addRow("Cantidad:", spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            self.add_to_cart(product, spin.value())
    
    def add_to_cart(self, product, qty):
        for item in self.cart:
            if item["batch_id"] == product["batch_id"]:
                new_qty = item["quantity"] + qty
                if new_qty > product["quantity"]:
                    QMessageBox.warning(self, "Stock insuficiente", f"Solo hay {product['quantity']} unidades.")
                    return
                item["quantity"] = new_qty
                item["subtotal"] = item["quantity"] * item["price"]
                self.update_cart_table()
                self.update_total()
                return
        self.cart.append({
            "product_name": product["name"],
            "batch_id": product["batch_id"],
            "quantity": qty,
            "price": product["price"],
            "subtotal": qty * product["price"],
            "code": product["code"]
        })
        self.update_cart_table()
        self.update_total()
    
    def update_cart_table(self):
        self.cart_table.setRowCount(len(self.cart))
        total_units = 0
        for row, item in enumerate(self.cart):
            self.cart_table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.cart_table.setItem(row, 1, QTableWidgetItem(str(item["quantity"])))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{item['price']:.2f}"))
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"{item['subtotal']:.2f}"))
            del_btn = QPushButton("❌")
            del_btn.clicked.connect(lambda _, r=row: self.remove_from_cart(r))
            self.cart_table.setCellWidget(row, 4, del_btn)
            edit_btn = QPushButton("✏️")
            edit_btn.clicked.connect(lambda _, r=row: self.edit_cart_item(r))
            self.cart_table.setCellWidget(row, 5, edit_btn)
            total_units += item["quantity"]
        self.item_count_label.setText(f"{len(self.cart)} items | {total_units} unidades")
    
    def remove_from_cart(self, row):
        del self.cart[row]
        self.update_cart_table()
        self.update_total()
    
    def edit_cart_item(self, row):
        item = self.cart[row]
        product = next((p for p in self.all_products if p["batch_id"] == item["batch_id"]), None)
        if not product:
            QMessageBox.warning(self, "Error", "Producto no encontrado.")
            return
        max_qty = product["quantity"] + item["quantity"]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Editar cantidad - {item['product_name']}")
        layout = QFormLayout()
        spin = QSpinBox()
        spin.setRange(1, max_qty)
        spin.setValue(item["quantity"])
        layout.addRow("Nueva cantidad:", spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            new_qty = spin.value()
            if new_qty > max_qty:
                QMessageBox.warning(self, "Error", "Cantidad excede el stock disponible.")
                return
            item["quantity"] = new_qty
            item["subtotal"] = new_qty * item["price"]
            self.update_cart_table()
            self.update_total()
    
    def clear_cart(self):
        if self.cart and QMessageBox.question(self, "Limpiar carrito", "¿Eliminar todos los productos del carrito?") == QMessageBox.Yes:
            self.cart.clear()
            self.update_cart_table()
            self.update_total()
    
    def update_total(self):
        total = sum(item["subtotal"] for item in self.cart)
        self.total_label.setText(f"Total: {total:.2f} CUP")
    
    def process_payment(self):
        if not self.cart:
            QMessageBox.information(self, "Carrito vacío", "No hay productos en el carrito.")
            return
        total = sum(item["subtotal"] for item in self.cart)
        dialog = QDialog(self)
        dialog.setWindowTitle("Pago")
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
        def toggle_visible(idx):
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
        method = method_combo.currentText()
        change = 0.0
        if method == "Efectivo":
            received = cash_received.value()
            if received < total:
                QMessageBox.warning(self, "Pago insuficiente", f"El cliente entregó {received} CUP, total {total} CUP.")
                return
            change = received - total
            QMessageBox.information(self, "Vuelto", f"Vuelto: {change:.2f} CUP")
        reply = QMessageBox.question(self, "Confirmar venta", f"Total: {total:.2f} CUP\nMétodo: {method}\n¿Confirmar?")
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
            sale_id = register_sale(
                db=self.db,
                items=items_for_sale,
                payment_method=method,
                total=total,
                change_given=change,
                user_id=self.user.id
            )
            receipt_text = self.generate_receipt_text(sale_id, total, method, change, self.cart)
            self.show_receipt_dialog(receipt_text)
            QMessageBox.information(self, "Venta exitosa", f"Venta registrada con ID {sale_id}\nTiquete enviado a impresora.")
            self.cart.clear()
            self.update_cart_table()
            self.update_total()
            self.load_all_products()
            self.update_sales_summary()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta: {str(e)}")
    
    def generate_receipt_text(self, sale_id, total, method, change, items):
        settings = get_company_settings(self.db)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        lines.append("=" * 32)
        lines.append(f"{settings.company_name:^32}")
        if settings.nif:
            lines.append(f"NIF: {settings.nif}")
        if settings.phone:
            lines.append(f"Tel: {settings.phone}")
        if settings.address:
            lines.append(f"{settings.address[:32]}")
        lines.append("=" * 32)
        lines.append(f"Fecha: {now}")
        lines.append(f"Venta #: {sale_id}")
        lines.append(f"Atendido por: {self.user.username}")
        lines.append("-" * 32)
        for item in items:
            name = item["product_name"][:20]
            lines.append(name)
            lines.append(f"  {item['quantity']} x {item['price']:.2f} = {item['subtotal']:.2f}")
        lines.append("-" * 32)
        lines.append(f"TOTAL: {total:.2f} {settings.currency}")
        lines.append(f"Método: {method}")
        if method == "Efectivo":
            lines.append(f"Vuelto: {change:.2f} {settings.currency}")
        if settings.tax_rate > 0:
            tax_amount = total * settings.tax_rate / 100
            lines.append(f"Impuesto ({settings.tax_rate:.0f}%): {tax_amount:.2f} {settings.currency}")
        lines.append("=" * 32)
        lines.append(f"{settings.receipt_footer[:32]:^32}")
        lines.append("\n\n\n\n")
        return "\n".join(lines)
        
    def print_receipt(self, receipt_text):
        if WIN32_PRINT_AVAILABLE:
            try:
                default_printer = win32print.GetDefaultPrinter()
                hprinter = win32print.OpenPrinter(default_printer)
                try:
                    win32print.StartDocPrinter(hprinter, 1, ("Ticket", None, "RAW"))
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, receipt_text.encode('cp850', errors='replace'))
                    win32print.EndPagePrinter(hprinter)
                finally:
                    win32print.EndDocPrinter(hprinter)
                return
            except Exception as e:
                print(f"Error imprimiendo: {e}")
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(receipt_text)
                temp_path = f.name
            subprocess.run(['notepad', '/pt', temp_path], shell=True)
            os.unlink(temp_path)
        except Exception as e:
            print(f"Error guardando tiquete: {e}")
    
    def update_sales_summary(self):
        today = date.today()
        first_day_month = date(today.year, today.month, 1)
        daily_total = self.db.query(func.sum(Sale.total)).filter(Sale.created_at >= today).scalar() or 0.0
        monthly_total = self.db.query(func.sum(Sale.total)).filter(Sale.created_at >= first_day_month).scalar() or 0.0
        self.daily_label.setText(f"Ventas hoy: {daily_total:.2f} CUP")
        self.monthly_label.setText(f"Ventas mes: {monthly_total:.2f} CUP")