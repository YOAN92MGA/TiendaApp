from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QFrame, QWidget)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

class NotificationDialog(QDialog):
    def __init__(self, notifications, parent=None):
        super().__init__(parent)
        self.notifications = notifications
        self.setWindowTitle("Notificaciones importantes")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F7FA;
            }
            QLabel {
                color: #2C3E50;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("📢 Notificaciones del sistema")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2C3E50; margin: 10px;")
        layout.addWidget(title)
        
        # Área de scroll para las notificaciones
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # --- Productos próximos a vencer ---
        expiring = notifications.get('expiring_products', [])
        if expiring:
            exp_label = QLabel("⚠️ Productos próximos a vencer (15 días)")
            exp_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            exp_label.setStyleSheet("color: #E67E22;")
            scroll_layout.addWidget(exp_label)
            
            for p in expiring[:10]:  # límite de 10
                item = QLabel(f"• {p['product_name']} (Cód: {p['code']}) - Vence: {p['expiration_date']} - Stock: {p['quantity']}")
                item.setWordWrap(True)
                item.setStyleSheet("color: #E74C3C; margin-left: 20px;")
                scroll_layout.addWidget(item)
            if len(expiring) > 10:
                scroll_layout.addWidget(QLabel(f"... y {len(expiring)-10} más."))
        
        # --- Productos con margen bajo ---
        low_margin = notifications.get('low_margin_products', [])
        if low_margin:
            margin_label = QLabel("💰 Productos con margen de ganancia bajo (<10%)")
            margin_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            margin_label.setStyleSheet("color: #E67E22; margin-top: 15px;")
            scroll_layout.addWidget(margin_label)
            
            for p in low_margin[:10]:
                item = QLabel(f"• {p['product_name']} (Cód: {p['code']}) - Margen: {p['margin']}% | Precio venta: ${p['sale_price']:.2f} | Costo prom: ${p['avg_cost']:.2f}")
                item.setWordWrap(True)
                item.setStyleSheet("color: #E74C3C; margin-left: 20px;")
                scroll_layout.addWidget(item)
            if len(low_margin) > 10:
                scroll_layout.addWidget(QLabel(f"... y {len(low_margin)-10} más."))
        
        # Si no hay notificaciones
        if not expiring and not low_margin:
            no_notif = QLabel("✅ No hay notificaciones pendientes. Todo está en orden.")
            no_notif.setFont(QFont("Segoe UI", 12))
            no_notif.setAlignment(Qt.AlignCenter)
            no_notif.setStyleSheet("color: #27AE60; margin: 20px;")
            scroll_layout.addWidget(no_notif)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Botón Aceptar
        btn_ok = QPushButton("Aceptar")
        btn_ok.setFixedSize(100, 35)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)