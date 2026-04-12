# ui/product_entry_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDateEdit, QMessageBox,
    QListWidget, QListWidgetItem, QSpinBox, QCheckBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QDate, Qt
from sqlalchemy.orm import Session
from services.product_service import add_multiple_batches

class ProductEntryWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.products_to_add = []
        self.setWindowTitle("Entrada de Productos")
        self.setStyleSheet("background-color: #F3F6FB;")

        # Layout principal
        layout = QVBoxLayout()

        # --- Campos en fila horizontal ---
        fields_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre producto")
        self.category_input = QComboBox()
        self.category_input.addItems([
            "Calzado", "Liquidos", "Carnicos", "Confituras",
            "Granos", "Ropas", "Productos Especiales"
        ])
        self.price_cup_input = QLineEdit()
        self.price_cup_input.setPlaceholderText("Precio compra CUP")
        self.usd_rate_input = QLineEdit()
        self.usd_rate_input.setPlaceholderText("Tipo cambio USD")
        self.sale_price_input = QLineEdit()
        self.sale_price_input.setPlaceholderText("Precio venta")
        self.expiration_input = QDateEdit()
        self.expiration_input.setDate(QDate.currentDate())
        self.supplier_input = QLineEdit()
        self.supplier_input.setPlaceholderText("Proveedor")
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 9999)
        self.quantity_input.setValue(1)
        # Checkbox para producto especial
        self.special_checkbox = QCheckBox("Producto Especial")
        self.special_checkbox.setChecked(False)

        # Aplicar altura fija a todos los widgets
        for w in [self.name_input, self.category_input, self.price_cup_input,
                  self.usd_rate_input, self.sale_price_input, self.expiration_input,
                  self.supplier_input, self.quantity_input, self.special_checkbox]:
            w.setFixedHeight(30)
            fields_layout.addWidget(w)

        layout.addLayout(fields_layout)

        # --- Botones agregar / finalizar ---
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Agregar")
        self.finalize_btn = QPushButton("Finalizar")
        self.add_btn.setStyleSheet("background-color: #AEDFF7; border-radius: 5px; padding: 8px;")
        self.finalize_btn.setStyleSheet("background-color: #7BC8F6; border-radius: 5px; padding: 8px;")
        self.add_btn.clicked.connect(self.add_product)
        self.finalize_btn.clicked.connect(self.finalize_entry)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.finalize_btn)
        layout.addLayout(button_layout)

        # --- Lista productos agregados ---
        layout.addWidget(QLabel("Productos a ingresar:"))
        self.product_list_widget = QListWidget()
        layout.addWidget(self.product_list_widget)

        self.setLayout(layout)

    def add_product(self):
        try:
            name = self.name_input.text().strip()
            if not name:
                raise ValueError("Nombre de producto requerido")

            category = self.category_input.currentText()
            price_cup = float(self.price_cup_input.text())
            usd_rate = float(self.usd_rate_input.text())
            sale_price = float(self.sale_price_input.text())
            expiration = self.expiration_input.date().toPython()
            supplier = self.supplier_input.text().strip()
            quantity = self.quantity_input.value()
            is_special = self.special_checkbox.isChecked()   # <--- definimos la variable

            if price_cup <= 0 or usd_rate <= 0 or sale_price <= 0 or quantity <= 0:
                raise ValueError("Todos los valores deben ser positivos")

            product_info = {
                "name": name,
                "category": category,
                "purchase_price_cup": price_cup,
                "usd_rate": usd_rate,
                "sale_price": sale_price,
                "expiration_date": expiration,
                "supplier": supplier,
                "quantity": quantity,
                "is_special": self.special_checkbox.isChecked()   # <--- agregar esta línea
            }
            self.products_to_add.append(product_info)

            # Agregar a la lista visual
            icons = {
                "Calzado": "assets/icons/calzado.png",
                "Liquidos": "assets/icons/liquidos.png",
                "Carnicos": "assets/icons/carnicos.png",
                "Confituras": "assets/icons/confituras.png",
                "Granos": "assets/icons/granos.png",
                "Ropas": "assets/icons/ropas.png",
                "Productos Especiales": "assets/icons/especiales.png"
            }
            icon_path = icons.get(category, "")
            special_tag = " [ESPECIAL]" if is_special else ""
            item_text = (f"{name}{special_tag} | {category} | {quantity} uds | "
                         f"Compra: {price_cup:.2f} CUP | Venta: {sale_price:.2f} CUP | "
                         f"Vence: {expiration.strftime('%d/%m/%Y')}")
            item = QListWidgetItem(QIcon(icon_path), item_text)
            self.product_list_widget.addItem(item)

            # Limpiar campos excepto categoría y fecha
            self.name_input.clear()
            self.price_cup_input.clear()
            self.usd_rate_input.clear()
            self.sale_price_input.clear()
            self.supplier_input.clear()
            self.quantity_input.setValue(1)
            self.special_checkbox.setChecked(False)
            self.name_input.setFocus()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Datos inválidos: {str(e)}")

    def finalize_entry(self):
        if not self.products_to_add:
            QMessageBox.information(self, "Sin productos", "No hay productos para ingresar.")
            return

        total_items = len(self.products_to_add)
        total_units = sum(p["quantity"] for p in self.products_to_add)
        msg = f"¿Confirmar entrada de {total_items} productos ({total_units} unidades)?\n\n"
        for p in self.products_to_add:
            special = " [ESPECIAL]" if p.get("is_special", False) else ""
            msg += f"- {p['name']}{special} ({p['category']}): {p['quantity']} uds\n"
        reply = QMessageBox.question(self, "Confirmar entrada", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            batches = add_multiple_batches(self.db, self.products_to_add, self.user.id)
            QMessageBox.information(self, "Éxito", f"Se han ingresado {len(batches)} lotes correctamente.")
            self.products_to_add.clear()
            self.product_list_widget.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")