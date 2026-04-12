from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from sqlalchemy.orm import Session
from services.company_service import get_company_settings
from services.report_service import get_sales_by_period, get_top_products, get_profit_vs_expenses
import os

def generate_sales_report_pdf(db: Session, start_date, end_date, filename="reporte_ventas.pdf"):
    """Genera reporte completo de ventas, productos y ganancias en PDF."""
    
    # Obtener datos
    sales_data = get_sales_by_period(db, start_date, end_date)
    top_products = get_top_products(db, limit=10)
    profit_data = get_profit_vs_expenses(db, start_date.year, start_date.month)  # Simplificado
    
    # Crear documento
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = []
    
    # Estilos personalizados
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=16)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    
    # Logo y datos de la empresa
    company = get_company_settings(db)
    if company.logo_path and os.path.exists(company.logo_path):
        try:
            img = Image(company.logo_path, width=1.5*inch, height=1.5*inch)
            story.append(img)
        except:
            pass
    
    story.append(Paragraph(company.company_name or "Mi Tienda", title_style))
    story.append(Paragraph(f"NIF: {company.nif or ''} | Tel: {company.phone or ''}", subtitle_style))
    story.append(Paragraph(f"Periodo: {start_date} al {end_date}", subtitle_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Tabla de ventas diarias
    if sales_data:
        data = [["Fecha", "Total (CUP)"]]
        total_ventas = 0
        for row in sales_data:
            data.append([row['day'], f"{row['total']:.2f}"])
            total_ventas += row['total']
        data.append(["", ""])
        data.append(["TOTAL GENERAL", f"{total_ventas:.2f}"])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-2), 1, colors.black),
            ('BOX', (0,-1), (-1,-1), 2, colors.black),
        ]))
        story.append(Paragraph("Resumen de Ventas Diarias", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    # Top productos más vendidos
    if top_products:
        data2 = [["Producto", "Código", "Cantidad vendida"]]
        for prod in top_products:
            data2.append([prod['name'], prod['code'], str(prod['quantity'])])
        
        table2 = Table(data2)
        table2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        story.append(Paragraph("Productos más vendidos", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        story.append(table2)
        story.append(Spacer(1, 0.3*inch))
    
    # Resumen de ganancias y gastos
    story.append(Paragraph("Resumen Financiero", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    profit_data_display = [
        ["Concepto", "Monto (CUP)"],
        ["Ventas totales", f"{profit_data.get('total_sales', 0):.2f}"],
        ["Costo de ventas", f"{profit_data.get('total_cost', 0):.2f}"],
        ["Ganancia bruta", f"{profit_data.get('gross_profit', 0):.2f}"],
        ["Gastos operativos", f"{profit_data.get('total_expenses', 0):.2f}"],
        ["Ganancia neta", f"{profit_data.get('net_profit', 0):.2f}"]
    ]
    
    table3 = Table(profit_data_display)
    table3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    story.append(table3)
    
    # Pie de página
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Reporte generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    
    # Construir PDF
    doc.build(story)
    return filename