# ui/dashboard.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QLabel
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from ui.pos_window import POSWindow
from ui.product_entry_window import ProductEntryWindow
from ui.transfer_window import TransferWindow
from ui.warehouse_window import WarehouseWindow
from ui.expenses_window import ExpensesWindow
from ui.inventory_window import InventoryWindow
from ui.special_products_window import SpecialProductsWindow
from ui.reports_window import ReportsWindow
from ui.users_window import UsersWindow
from ui.backup_window import BackupWindow
from ui.history_window import HistoryWindow
from ui.home_window import HomeWindow
from services.notification_service import get_startup_notifications
from ui.notification_dialog import NotificationDialog

class Dashboard(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Sistema de Gestión de Tienda")
        self.showMaximized()
        self.show_startup_notifications()
        
        # Layout principal vertical
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Barra superior con título y botón de salida ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(15, 10, 15, 10)
        title_label = QLabel("🏪 Sistema de Gestión de Tienda")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: #2C3E50;")
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        logout_btn = QPushButton("🔒 Cerrar sesión")
        logout_btn.setStyleSheet("background-color: #E74C3C; border-radius: 6px; padding: 6px 12px;")
        logout_btn.clicked.connect(self.logout)
        top_bar.addWidget(logout_btn)
        main_layout.addLayout(top_bar)

        # --- Barra de botones de módulos ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setAlignment(Qt.AlignLeft)
        button_layout.setContentsMargins(15, 5, 15, 5)

        # Lista completa de módulos (nombre, clave, rol mínimo requerido)
        all_modules = [
             ("🏠 Inicio", "home", "employee"),   # <-- nuevo
            ("🛒 Ventas", "sales", "employee"),
            ("📦 Entrada", "entry", "admin"),
            ("🔄 Transferencias", "transfer", "admin"),
            ("🏚️ Almacén", "warehouse", "admin"),
            ("💰 Gastos", "expenses", "admin"),
            ("📊 Inventario", "inventory", "admin"),      # solo admin
            ("⭐ Especiales", "specials", "admin"),
            ("📈 Reportes", "reports", "admin"),          # solo admin
            ("👥 Usuarios", "users", "admin"),             # solo admin
            ("💾 Copias", "backup", "admin"),
            ("📜 Historial", "history", "admin")
            ]

        # Filtrar según rol del usuario
        modules_list = [(label, key) for label, key, role_needed in all_modules 
            if role_needed == "employee" or self.user.role == "admin"]

        self.buttons = {}
        for label, key in modules_list:
            btn = QPushButton(label)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setMinimumHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #2C3E50;
                    border: 1px solid #D0D7DE;
                    border-radius: 10px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #E8F0FE;
                    border-color: #4A90E2;
                }
                QPushButton:pressed {
                    background-color: #D0E0F5;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self.switch_module(k))
            button_layout.addWidget(btn)
            self.buttons[key] = btn

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # --- Área dinámica (stacked widget) ---
        self.dynamic_area = QStackedWidget()
        self.dynamic_area.setStyleSheet("background-color: #F5F7FA; border-radius: 12px;")
        main_layout.addWidget(self.dynamic_area, 1)

        # --- Instanciar módulos ---
        self.modules = {}
        self.modules["sales"] = POSWindow(self.db, self.user)
        self.modules["entry"] = ProductEntryWindow(self.db, self.user)
        self.modules["transfer"] = TransferWindow(self.db, self.user)
        self.modules["warehouse"] = WarehouseWindow(self.db, self.user)
        self.modules["expenses"] = ExpensesWindow(self.db, self.user)
        self.modules["inventory"] = InventoryWindow(self.db, self.user)
        self.modules["specials"] = SpecialProductsWindow(self.db, self.user)
        self.modules["reports"] = ReportsWindow(self.db, self.user)
        self.modules["users"] = UsersWindow(self.db, self.user)
        self.modules["backup"] = BackupWindow(self.db, self.user)
        self.modules["history"] = HistoryWindow(self.db, self.user)
        self.modules["home"] = HomeWindow(self.db, self.user)
        
        
        for key, module in self.modules.items():
            self.dynamic_area.addWidget(module)

        # Módulo inicial
        self.switch_module("home")

        self.setLayout(main_layout)

    def switch_module(self, key):
        """Muestra el módulo seleccionado y resalta su botón."""
        if key in self.modules:
            self.dynamic_area.setCurrentWidget(self.modules[key])
            # Resaltar botón activo
            for k, btn in self.buttons.items():
                if k == key:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4A90E2;
                            color: white;
                            border: none;
                            border-radius: 10px;
                            padding: 8px 16px;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #2C3E50;
                            border: 1px solid #D0D7DE;
                            border-radius: 10px;
                            padding: 8px 16px;
                        }
                        QPushButton:hover {
                            background-color: #E8F0FE;
                        }
                    """)

    def logout(self):
        from PySide6.QtWidgets import QMessageBox, QApplication
        reply = QMessageBox.question(self, "Cerrar sesión", "¿Está seguro de que desea cerrar sesión?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            QApplication.quit()
    def show_startup_notifications(self):
        notifications = get_startup_notifications(self.db)
        # Solo mostrar si hay al menos una notificación
        if notifications['expiring_products'] or notifications['low_margin_products']:
            dialog = NotificationDialog(notifications, self)
            dialog.exec()