# ui/dashboard.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QSize

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
from PySide6.QtWidgets import QLabel
from ui.company_config_window import CompanyConfigWindow
from ui.cash_register_window import CashRegisterWindow
from ui.sync_window import SyncWindow
from ui.cash_close_window import CashCloseWindow
from ui.profit_window import ProfitWindow

class Dashboard(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Sistema de Gestión de Tienda")
        self.resize(1100, 700)
        self.setMinimumSize(800, 600)
        
        # Mostrar notificaciones al inicio
        self.show_startup_notifications()
        
        # Layout principal horizontal (splitter manual)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== PANEL IZQUIERDO (barra lateral de botones) ==========
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.NoFrame)
        left_panel.setStyleSheet("background-color: #1E293B;")  # fondo oscuro moderno
        left_panel.setFixedWidth(240)  # ancho fijo
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 20, 10, 20)
        left_layout.setSpacing(8)
        
        # Título del sistema en la barra lateral
        title_label = QLabel("🏪 Mi Tienda")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: white; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)
        
        # Scroll area para los botones
        scroll_buttons = QScrollArea()
        scroll_buttons.setWidgetResizable(True)
        scroll_buttons.setFrameShape(QFrame.NoFrame)
        scroll_buttons.setStyleSheet("background-color: transparent; border: none;")
        
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(6)
        
        # Lista completa de módulos (nombre, clave, rol mínimo requerido)
        all_modules = [
            ("🏠 Inicio", "home", "employee"),
            ("🛒 Ventas", "sales", "employee"),
            ("📦 Entrada", "entry", "admin"),
            ("🔄 Transferencias", "transfer", "admin"),
            ("🏚️ Almacén", "warehouse", "admin"),
            ("💰 Gastos", "expenses", "admin"),
            ("📈 Utilidades", "profit", "admin"),
            ("📊 Inventario", "inventory", "admin"),
            ("⭐ Especiales", "specials", "admin"),
            ("📈 Reportes", "reports", "admin"),
            ("👥 Usuarios", "users", "admin"),
            ("💾 Copias", "backup", "admin"),
            ("📜 Historial", "history", "admin"),
            ("⚙️ Configuración", "company", "admin"),
            ("💰 Gestión de cajas", "cash", "admin"),
            ("🔄 Sincronización", "sync", "admin"),
            ("🔒 Cerrar caja", "cashclose", "admin"),
        ]
        
        # Filtrar según rol del usuario
        modules_list = [(label, key) for label, key, role_needed in all_modules 
                        if role_needed == "employee" or self.user.role == "admin"]
        
        self.buttons = {}
        for label, key in modules_list:
            btn = QPushButton(label)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setMinimumHeight(44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #CBD5E1;
                    text-align: left;
                    padding: 8px 12px;
                    border-radius: 8px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #0F172A;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self.switch_module(k))
            buttons_layout.addWidget(btn)
            self.buttons[key] = btn
        
        buttons_layout.addStretch()
        scroll_buttons.setWidget(buttons_container)
        left_layout.addWidget(scroll_buttons)
        
        # Botón de cerrar sesión al final
        logout_btn = QPushButton("🔒 Cerrar sesión")
        logout_btn.setFont(QFont("Segoe UI", 11))
        logout_btn.setMinimumHeight(44)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border-radius: 8px;
                padding: 8px 12px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        left_layout.addWidget(logout_btn)
        
        # ========== PANEL DERECHO (contenido dinámico) ==========
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #F8FAFC;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.dynamic_area = QStackedWidget()
        self.dynamic_area.setStyleSheet("background-color: #F8FAFC;")
        right_layout.addWidget(self.dynamic_area)
        
        # Instanciar módulos
        self.modules = {}
        self.modules["home"] = HomeWindow(self.db, self.user)
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
        self.modules["company"] = CompanyConfigWindow(self.db, self.user)
        self.modules["cash"] = CashRegisterWindow(self.db, self.user)
        self.modules["sync"] = SyncWindow(self.db, self.user)
        self.modules["cashclose"] = CashCloseWindow(self.db, self.user)
        self.modules["profit"] = ProfitWindow(self.db, self.user)
        for key, module in self.modules.items():
            self.dynamic_area.addWidget(module)
        
        # Agregar paneles al layout principal
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)  # el derecho se expande
        
        self.setLayout(main_layout)
        
        # Módulo inicial
        self.switch_module("home")
    
    def switch_module(self, key):
        """Muestra el módulo seleccionado y resalta su botón."""
        if key in self.modules:
            self.dynamic_area.setCurrentWidget(self.modules[key])
            # Resaltar botón activo
            for k, btn in self.buttons.items():
                if k == key:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3B82F6;
                            color: white;
                            text-align: left;
                            padding: 8px 12px;
                            border-radius: 8px;
                            border: none;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            color: #CBD5E1;
                            text-align: left;
                            padding: 8px 12px;
                            border-radius: 8px;
                            border: none;
                        }
                        QPushButton:hover {
                            background-color: #334155;
                            color: white;
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
        if notifications['expiring_products'] or notifications['low_margin_products']:
            dialog = NotificationDialog(notifications, self)
            dialog.exec()