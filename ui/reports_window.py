# ui/reports_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import date
from datetime import timedelta
from services.report_service import (
    get_sales_by_period, get_monthly_sales, get_top_products,
    get_profit_vs_expenses, get_expiring_products, get_low_margin_products,
    export_to_excel
)

class ReportsWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Reportes y Estadísticas")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #F5F7FA;")

        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # Pestaña 1: Ventas
        self.sales_tab = QWidget()
        self.setup_sales_tab()
        self.tabs.addTab(self.sales_tab, "📈 Ventas")
        
        # Pestaña 2: Productos más vendidos
        self.top_products_tab = QWidget()
        self.setup_top_products_tab()
        self.tabs.addTab(self.top_products_tab, "🏆 Top Productos")
        
        # Pestaña 3: Ganancias vs Gastos
        self.profit_tab = QWidget()
        self.setup_profit_tab()
        self.tabs.addTab(self.profit_tab, "💰 Ganancias vs Gastos")
        
        # Pestaña 4: Alertas
        self.alerts_tab = QWidget()
        self.setup_alerts_tab()
        self.tabs.addTab(self.alerts_tab, "⚠️ Alertas")
        
        # Después de self.tabs.addTab(self.alerts_tab, "⚠️ Alertas")
        self.profit_daily_tab = QWidget()       
        self.setup_profit_daily_tab()
        self.tabs.addTab(self.profit_daily_tab, "📊 Ganancias Diarias")
        
        # Botón exportar global (opcional)
        export_btn = QPushButton("📎 Exportar todo a Excel")
        export_btn.clicked.connect(self.export_all)
        layout.addWidget(export_btn, alignment=Qt.AlignRight)
        
        # Botón exportar a PDF (corregido)
        self.pdf_btn = QPushButton("📄 Exportar a PDF")
        self.pdf_btn.clicked.connect(self.export_pdf)
        layout.addWidget(self.pdf_btn, alignment=Qt.AlignRight)
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
        # Cargar datos iniciales en cada pestaña
        self.refresh_all()
    def setup_profit_daily_tab(self):
        layout = QVBoxLayout(self.profit_daily_tab)
        
        # Filtros
        filter_layout = QHBoxLayout()
        self.profit_start_date = QDateEdit()
        self.profit_start_date.setDate(QDate.currentDate().addDays(-30))
        self.profit_start_date.setCalendarPopup(True)
        self.profit_end_date = QDateEdit()
        self.profit_end_date.setDate(QDate.currentDate())
        self.profit_end_date.setCalendarPopup(True)
        self.refresh_profit_btn = QPushButton("Actualizar")
        self.refresh_profit_btn.clicked.connect(self.refresh_daily_profit)
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.profit_start_date)
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.profit_end_date)
        filter_layout.addWidget(self.refresh_profit_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Tabla de ganancias diarias
        self.profit_daily_table = QTableWidget()
        self.profit_daily_table.setColumnCount(4)
        self.profit_daily_table.setHorizontalHeaderLabels(["Fecha", "Ventas (CUP)", "Costo (CUP)", "Ganancia (CUP)"])
        self.profit_daily_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.profit_daily_table)
        
        # Gráfico de ganancias
        self.profit_figure = Figure(figsize=(5, 3))
        self.profit_canvas = FigureCanvas(self.profit_figure)
        layout.addWidget(self.profit_canvas)
        
        # Cargar datos iniciales
        self.refresh_daily_profit()
        
    def refresh_daily_profit(self):
        from services.report_service import get_daily_profit
        start = self.profit_start_date.date().toPython()
        end = self.profit_end_date.date().toPython()
        data = get_daily_profit(self.db, start, end)
        if not data:
            self.profit_daily_table.setRowCount(1)
            self.profit_daily_table.setItem(0, 0, QTableWidgetItem("Sin datos"))
            return
        self.profit_daily_table.setRowCount(len(data))
        days = []
        profits = []
        for row, d in enumerate(data):
            self.profit_daily_table.setItem(row, 0, QTableWidgetItem(d["day"]))
            self.profit_daily_table.setItem(row, 1, QTableWidgetItem(f"{d['sales']:.2f}"))
            self.profit_daily_table.setItem(row, 2, QTableWidgetItem(f"{d['cost']:.2f}"))
            self.profit_daily_table.setItem(row, 3, QTableWidgetItem(f"{d['profit']:.2f}"))
            days.append(d["day"])
            profits.append(d["profit"])
        # Graficar
        self.profit_figure.clear()
        ax = self.profit_figure.add_subplot(111)
        ax.bar(days, profits, color='#2ECC71')
        ax.set_title("Ganancia diaria")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Ganancia (CUP)")
        ax.tick_params(axis='x', rotation=45)
        self.profit_figure.tight_layout()
        self.profit_canvas.draw()    
        
    def setup_sales_tab(self):
        layout = QVBoxLayout(self.sales_tab)
        
        # Filtros
        filter_layout = QHBoxLayout()
        self.sales_period_combo = QComboBox()
        self.sales_period_combo.addItems(["Diario (últimos 30 días)", "Mensual (año actual)"])
        self.sales_period_combo.currentIndexChanged.connect(self.refresh_sales)
        filter_layout.addWidget(QLabel("Ver:"))
        filter_layout.addWidget(self.sales_period_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Gráfico
        self.sales_figure = Figure(figsize=(5, 3))
        self.sales_canvas = FigureCanvas(self.sales_figure)
        layout.addWidget(self.sales_canvas)
        
        # Tabla de datos
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(2)
        self.sales_table.setHorizontalHeaderLabels(["Período", "Total (CUP)"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.sales_table)
    
    def setup_top_products_tab(self):
        layout = QVBoxLayout(self.top_products_tab)
        self.top_products_table = QTableWidget()
        self.top_products_table.setColumnCount(3)
        self.top_products_table.setHorizontalHeaderLabels(["Código", "Producto", "Unidades vendidas"])
        self.top_products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.top_products_table)
    
    def setup_profit_tab(self):
        layout = QVBoxLayout(self.profit_tab)
        
        # Selector de año/mes
        filter_layout = QHBoxLayout()
        self.profit_year_combo = QComboBox()
        current_year = date.today().year
        for y in range(current_year-2, current_year+1):
            self.profit_year_combo.addItem(str(y))
        self.profit_month_combo = QComboBox()
        self.profit_month_combo.addItem("Todo el año")
        for m in range(1, 13):
            self.profit_month_combo.addItem(f"Mes {m}")
        self.profit_month_combo.currentIndexChanged.connect(self.refresh_profit)
        self.profit_year_combo.currentIndexChanged.connect(self.refresh_profit)
        filter_layout.addWidget(QLabel("Año:"))
        filter_layout.addWidget(self.profit_year_combo)
        filter_layout.addWidget(QLabel("Mes:"))
        filter_layout.addWidget(self.profit_month_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Etiquetas de resultados
        self.profit_labels = {}
        metrics = ["Ventas totales", "Costo de ventas", "Ganancia bruta", "Gastos operativos", "Ganancia neta"]
        for metric in metrics:
            lbl = QLabel(f"{metric}: -- CUP")
            lbl.setStyleSheet("font-size: 14px; margin: 5px;")
            layout.addWidget(lbl)
            self.profit_labels[metric] = lbl
        
        # Gráfico de barras comparativo (opcional)
        self.profit_figure = Figure(figsize=(4, 2))
        self.profit_canvas = FigureCanvas(self.profit_figure)
        layout.addWidget(self.profit_canvas)
    
    def setup_alerts_tab(self):
        layout = QVBoxLayout(self.alerts_tab)
        # Subpestañas o secciones
        self.alerts_tabs = QTabWidget()
        
        # Próximos a vencer
        expiring_widget = QWidget()
        expiring_layout = QVBoxLayout(expiring_widget)
        self.expiring_table = QTableWidget()
        self.expiring_table.setColumnCount(4)
        self.expiring_table.setHorizontalHeaderLabels(["Producto", "Código", "Vencimiento", "Stock"])
        expiring_layout.addWidget(self.expiring_table)
        self.alerts_tabs.addTab(expiring_widget, "Próximos a vencer (≤15 días)")
        
        # Bajo margen
        low_margin_widget = QWidget()
        low_margin_layout = QVBoxLayout(low_margin_widget)
        self.low_margin_table = QTableWidget()
        self.low_margin_table.setColumnCount(5)
        self.low_margin_table.setHorizontalHeaderLabels(["Producto", "Código", "P. Venta", "P. Compra", "Margen %"])
        low_margin_layout.addWidget(self.low_margin_table)
        self.alerts_tabs.addTab(low_margin_widget, "Margen bajo (<30%)")
        
        layout.addWidget(self.alerts_tabs)
    
    def refresh_all(self):
        self.refresh_sales()
        self.refresh_top_products()
        self.refresh_profit()
        self.refresh_alerts()
    
    def refresh_sales(self):
        period = self.sales_period_combo.currentText()
        if "Diario" in period:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            data = get_sales_by_period(self.db, start_date, end_date)
            if not data:
                self.sales_table.setRowCount(1)
                self.sales_table.setItem(0, 0, QTableWidgetItem("Sin datos"))
                self.sales_table.setItem(0, 1, QTableWidgetItem("0"))
                return
            # Llenar tabla
            self.sales_table.setRowCount(len(data))
            days = []
            totals = []
            for row, d in enumerate(data):
                self.sales_table.setItem(row, 0, QTableWidgetItem(d["day"]))
                self.sales_table.setItem(row, 1, QTableWidgetItem(f"{d['total']:.2f}"))
                days.append(d["day"])
                totals.append(d["total"])
            # Graficar
            self.sales_figure.clear()
            ax = self.sales_figure.add_subplot(111)
            ax.bar(days, totals, color='#4A90E2')
            ax.set_title("Ventas diarias (últimos 30 días)")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Total CUP")
            ax.tick_params(axis='x', rotation=45)
            self.sales_figure.tight_layout()
            self.sales_canvas.draw()
        else:  # Mensual
            year = date.today().year
            data = get_monthly_sales(self.db, year)
            if not data:
                self.sales_table.setRowCount(1)
                self.sales_table.setItem(0, 0, QTableWidgetItem("Sin datos"))
                return
            self.sales_table.setRowCount(len(data))
            months = []
            totals = []
            for row, d in enumerate(data):
                self.sales_table.setItem(row, 0, QTableWidgetItem(f"Mes {d['month']}"))
                self.sales_table.setItem(row, 1, QTableWidgetItem(f"{d['total']:.2f}"))
                months.append(f"M{d['month']}")
                totals.append(d['total'])
            self.sales_figure.clear()
            ax = self.sales_figure.add_subplot(111)
            ax.bar(months, totals, color='#4A90E2')
            ax.set_title(f"Ventas mensuales {year}")
            ax.set_xlabel("Mes")
            ax.set_ylabel("Total CUP")
            self.sales_figure.tight_layout()
            self.sales_canvas.draw()
    
    def refresh_top_products(self):
        data = get_top_products(self.db, limit=15)
        self.top_products_table.setRowCount(len(data))
        for row, p in enumerate(data):
            self.top_products_table.setItem(row, 0, QTableWidgetItem(p["code"]))
            self.top_products_table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.top_products_table.setItem(row, 2, QTableWidgetItem(str(p["quantity"])))
    
    def refresh_profit(self):
        year = int(self.profit_year_combo.currentText())
        month_index = self.profit_month_combo.currentIndex()
        month = month_index if month_index > 0 else None
        stats = get_profit_vs_expenses(self.db, year, month)
        self.profit_labels["Ventas totales"].setText(f"Ventas totales: {stats['total_sales']:.2f} CUP")
        self.profit_labels["Costo de ventas"].setText(f"Costo de ventas: {stats['total_cost']:.2f} CUP")
        self.profit_labels["Ganancia bruta"].setText(f"Ganancia bruta: {stats['gross_profit']:.2f} CUP")
        self.profit_labels["Gastos operativos"].setText(f"Gastos operativos: {stats['total_expenses']:.2f} CUP")
        self.profit_labels["Ganancia neta"].setText(f"Ganancia neta: {stats['net_profit']:.2f} CUP")
        # Gráfico comparativo
        self.profit_figure.clear()
        ax = self.profit_figure.add_subplot(111)
        categories = ["Ventas", "Costo", "Gastos", "Ganancia neta"]
        values = [stats['total_sales'], stats['total_cost'], stats['total_expenses'], stats['net_profit']]
        colors = ['#4A90E2', '#E74C3C', '#F39C12', '#2ECC71']
        ax.bar(categories, values, color=colors)
        ax.set_title("Resumen financiero")
        ax.set_ylabel("CUP")
        self.profit_figure.tight_layout()
        self.profit_canvas.draw()
    
    def refresh_alerts(self):
        # Próximos a vencer
        expiring = get_expiring_products(self.db, 15)
        self.expiring_table.setRowCount(len(expiring))
        for row, p in enumerate(expiring):
            self.expiring_table.setItem(row, 0, QTableWidgetItem(p["product_name"]))
            self.expiring_table.setItem(row, 1, QTableWidgetItem(p["code"]))
            self.expiring_table.setItem(row, 2, QTableWidgetItem(p["expiration_date"].strftime("%Y-%m-%d")))
            self.expiring_table.setItem(row, 3, QTableWidgetItem(str(p["quantity"])))
        if not expiring:
            self.expiring_table.setRowCount(1)
            self.expiring_table.setSpan(0, 0, 1, 4)
            self.expiring_table.setItem(0, 0, QTableWidgetItem("No hay productos próximos a vencer"))
        
        # Bajo margen (usando tipo de cambio por defecto 24, pero se podría pedir al usuario)
        low_margin = get_low_margin_products(self.db, 30, 24.0)
        self.low_margin_table.setRowCount(len(low_margin))
        for row, p in enumerate(low_margin):
            self.low_margin_table.setItem(row, 0, QTableWidgetItem(p["product_name"]))
            self.low_margin_table.setItem(row, 1, QTableWidgetItem(p["code"]))
            self.low_margin_table.setItem(row, 2, QTableWidgetItem(f"{p['sale_price']:.2f}"))
            self.low_margin_table.setItem(row, 3, QTableWidgetItem(f"{p['purchase_price']:.2f}"))
            self.low_margin_table.setItem(row, 4, QTableWidgetItem(f"{p['margin']:.2f}%"))
        if not low_margin:
            self.low_margin_table.setRowCount(1)
            self.low_margin_table.setSpan(0, 0, 1, 5)
            self.low_margin_table.setItem(0, 0, QTableWidgetItem("No hay productos con margen bajo"))
    
    def export_all(self):
        """Exporta los datos actuales de cada pestaña a un archivo Excel con múltiples hojas."""
        try:
            with pd.ExcelWriter("reporte_completo.xlsx") as writer:
                # Ventas diarias
                sales_data = get_sales_by_period(self.db, date.today() - timedelta(days=30), date.today())
                if sales_data:
                    pd.DataFrame(sales_data).to_excel(writer, sheet_name="Ventas_diarias", index=False)
                # Ventas mensuales
                monthly = get_monthly_sales(self.db, date.today().year)
                if monthly:
                    pd.DataFrame(monthly).to_excel(writer, sheet_name="Ventas_mensuales", index=False)
                # Top productos
                top = get_top_products(self.db, 20)
                if top:
                    pd.DataFrame(top).to_excel(writer, sheet_name="Top_productos", index=False)
                # Alertas
                expiring = get_expiring_products(self.db, 15)
                if expiring:
                    pd.DataFrame(expiring).to_excel(writer, sheet_name="Por_vencer", index=False)
                low_margin = get_low_margin_products(self.db, 30, 24.0)
                if low_margin:
                    pd.DataFrame(low_margin).to_excel(writer, sheet_name="Bajo_margen", index=False)
            QMessageBox.information(self, "Exportación", "Reporte exportado a 'reporte_completo.xlsx'")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {str(e)}")
            
    def export_pdf(self):        
        from services.pdf_report_service import generate_sales_report_pdf
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QDateEdit, QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox
        from datetime import date, timedelta
        
        # Diálogo para seleccionar fechas
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleccionar periodo")
        layout = QVBoxLayout()
        form = QFormLayout()
        start_date_edit = QDateEdit()
        start_date_edit.setDate(date.today() - timedelta(days=30))
        start_date_edit.setCalendarPopup(True)
        end_date_edit = QDateEdit()
        end_date_edit.setDate(date.today())
        end_date_edit.setCalendarPopup(True)
        form.addRow("Fecha inicio:", start_date_edit)
        form.addRow("Fecha fin:", end_date_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        if dialog.exec() != QDialog.Accepted:
            return
        
        start_date = start_date_edit.date().toPython()
        end_date = end_date_edit.date().toPython()
        
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", f"reporte_{start_date}_a_{end_date}.pdf", "PDF (*.pdf)")
        if filename:
            try:
                generate_sales_report_pdf(self.db, start_date, end_date, filename)
                QMessageBox.information(self, "Éxito", f"Reporte guardado en {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo generar el PDF: {str(e)}")