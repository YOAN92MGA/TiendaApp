# ui/home_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
from sqlalchemy.orm import Session
from sqlalchemy import func  # <--- agregado
from datetime import date, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from models.sale import Sale
from models.batch import ProductBatch   # <--- corregido
from models.stock import Stock
from models.stock_location import StockLocation
from models.product import Product
from services.report_service import get_sales_by_period, get_expiring_products

class HomeWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Panel de Control")
        self.setStyleSheet("background-color: #F5F7FA;")

        # Layout principal con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        main_widget = QWidget()
        self.main_layout = QVBoxLayout(main_widget)
        scroll.setWidget(main_widget)
        
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

        # Título
        title = QLabel("📊 Panel de Control")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2C3E50; margin: 10px;")
        self.main_layout.addWidget(title)

        # Grid de tarjetas (2x2)
        self.card_grid = QGridLayout()
        self.card_grid.setSpacing(20)
        self.main_layout.addLayout(self.card_grid)

        # Sección de alertas
        self.alerts_label = QLabel("⚠️ Alertas importantes")
        self.alerts_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.alerts_label.setStyleSheet("color: #E74C3C; margin-top: 20px;")
        self.main_layout.addWidget(self.alerts_label)
        
        self.alerts_container = QVBoxLayout()
        self.main_layout.addLayout(self.alerts_container)

        # Temporizador para actualizar datos cada 60 segundos
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(60000)

        self.refresh_data()

    def create_card(self, title, value, icon, color):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 15px;
                border: 1px solid #E0E0E0;
            }}
        """)
        card.setMinimumHeight(120)
        layout = QVBoxLayout(card)
        
        top_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 24))
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12))
        title_label.setStyleSheet("color: #7F8C8D;")
        top_layout.addWidget(icon_label)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        return card

    def refresh_data(self):
        # Limpiar grid y alertas
        self.clear_layout(self.card_grid)
        self.clear_layout(self.alerts_container)

        today = date.today()
        first_day_month = date(today.year, today.month, 1)
        
        daily_sales = self.db.query(Sale).filter(Sale.created_at >= today).with_entities(func.sum(Sale.total)).scalar() or 0.0
        monthly_sales = self.db.query(Sale).filter(Sale.created_at >= first_day_month).with_entities(func.sum(Sale.total)).scalar() or 0.0
        total_stock = self.db.query(func.sum(Stock.quantity)).scalar() or 0
        unique_products = self.db.query(Product).join(ProductBatch, Product.id == ProductBatch.product_id).join(Stock, Stock.batch_id == ProductBatch.id).filter(Stock.quantity > 0).distinct().count()
        
        cards = [
            ("Ventas hoy", f"{daily_sales:,.2f} CUP", "💰", "#2ECC71"),
            ("Ventas del mes", f"{monthly_sales:,.2f} CUP", "📅", "#3498DB"),
            ("Unidades en stock", f"{total_stock:,}", "📦", "#F39C12"),
            ("Productos distintos", str(unique_products), "🏷️", "#9B59B6")
        ]
        
        for i, (title, value, icon, color) in enumerate(cards):
            card = self.create_card(title, value, icon, color)
            row = i // 2
            col = i % 2
            self.card_grid.addWidget(card, row, col)

        # Alertas: productos próximos a vencer
        expiring = get_expiring_products(self.db, 15)
        if expiring:
            alert_frame = QFrame()
            alert_frame.setStyleSheet("background-color: #FDEBD0; border-radius: 10px; padding: 10px;")
            alert_layout = QVBoxLayout(alert_frame)
            alert_layout.addWidget(QLabel("⚠️ Productos que vencen en los próximos 15 días:"))
            for p in expiring[:5]:
                alert_layout.addWidget(QLabel(f"• {p['product_name']} (Cód: {p['code']}) - Vence: {p['expiration_date']} - Stock: {p['quantity']}"))
            if len(expiring) > 5:
                alert_layout.addWidget(QLabel(f"... y {len(expiring)-5} más."))
            self.alerts_container.addWidget(alert_frame)
        else:
            no_alerts = QLabel("✅ No hay productos próximos a vencer.")
            no_alerts.setStyleSheet("color: #27AE60;")
            self.alerts_container.addWidget(no_alerts)

        # Gráfico de ventas últimos 7 días
        end_date = today
        start_date = today - timedelta(days=6)
        sales_data = get_sales_by_period(self.db, start_date, end_date)
        if sales_data:
            fig = Figure(figsize=(6, 3))
            ax = fig.add_subplot(111)
            days = [d['day'] for d in sales_data]
            totals = [d['total'] for d in sales_data]
            ax.bar(days, totals, color='#3498DB')
            ax.set_title("Ventas últimos 7 días")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("CUP")
            ax.tick_params(axis='x', rotation=45)
            fig.tight_layout()
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(250)
            self.main_layout.addWidget(QLabel("📈 Tendencia de ventas"))
            self.main_layout.addWidget(canvas)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())