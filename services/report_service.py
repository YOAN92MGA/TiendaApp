# services/report_service.py (versión que usa batch_id)
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models.sale import Sale
from models.transaction import Transaction
from models.expense import Expense
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.stock_location import StockLocation
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
import pandas as pd

def get_sales_by_period(db: Session, start_date: date, end_date: date) -> List[Dict]:
    results = (
        db.query(
            func.date(Sale.created_at).label("day"),
            func.sum(Sale.total).label("total")
        )
        .filter(Sale.created_at >= start_date, Sale.created_at <= end_date)
        .group_by(func.date(Sale.created_at))
        .order_by("day")
        .all()
    )
    return [{"day": r.day, "total": r.total} for r in results]

def get_monthly_sales(db: Session, year: int) -> List[Dict]:
    results = (
        db.query(
            extract('month', Sale.created_at).label("month"),
            func.sum(Sale.total).label("total")
        )
        .filter(extract('year', Sale.created_at) == year)
        .group_by(extract('month', Sale.created_at))
        .order_by("month")
        .all()
    )
    return [{"month": int(r.month), "total": r.total} for r in results]

def get_top_products(db: Session, limit: int = 10) -> List[Dict]:
    # Usamos batch_id, no product_batch_id
    results = (
        db.query(
            Product.name,
            Product.code,
            func.sum(Transaction.quantity).label("total_quantity")
        )
        .join(ProductBatch, Transaction.batch_id == ProductBatch.id)  # <-- batch_id
        .join(Product, ProductBatch.product_id == Product.id)
        .filter(Transaction.type == "sale")
        .group_by(Product.id)
        .order_by(func.sum(Transaction.quantity).desc())
        .limit(limit)
        .all()
    )
    return [{"name": r.name, "code": r.code, "quantity": r.total_quantity} for r in results]

def get_profit_vs_expenses(db: Session, year: int, month: int = None) -> Dict:
    query_sales = db.query(func.sum(Sale.total))
    if month:
        query_sales = query_sales.filter(
            extract('year', Sale.created_at) == year,
            extract('month', Sale.created_at) == month
        )
    else:
        query_sales = query_sales.filter(extract('year', Sale.created_at) == year)
    total_sales = query_sales.scalar() or 0.0

    # Costo de ventas: usamos batch_id
    cost_query = (
        db.query(func.sum(Transaction.quantity * ProductBatch.purchase_price_cup))
        .join(ProductBatch, Transaction.batch_id == ProductBatch.id)  # <-- batch_id
        .filter(Transaction.type == "sale")
    )
    if month:
        cost_query = cost_query.filter(
            extract('year', Transaction.created_at) == year,
            extract('month', Transaction.created_at) == month
        )
    else:
        cost_query = cost_query.filter(extract('year', Transaction.created_at) == year)
    total_cost = cost_query.scalar() or 0.0

    gross_profit = total_sales - total_cost

    # Gastos - asumiendo Expense tiene columna 'date'
    expense_query = db.query(func.sum(Expense.amount))
    if month:
        expense_query = expense_query.filter(
            extract('year', Expense.date) == year,
            extract('month', Expense.date) == month
        )
    else:
        expense_query = expense_query.filter(extract('year', Expense.date) == year)
    total_expenses = expense_query.scalar() or 0.0

    net_profit = gross_profit - total_expenses

    return {
        "total_sales": total_sales,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "total_expenses": total_expenses,
        "net_profit": net_profit
    }

def get_expiring_products(db: Session, days_threshold: int = 15) -> List[Dict]:
    today = date.today()
    limit_date = today + timedelta(days=days_threshold)
    batches = db.query(ProductBatch).filter(
        ProductBatch.quantity_remaining > 0,
        ProductBatch.expiration_date <= limit_date
    ).all()
    result = []
    for batch in batches:
        product = db.query(Product).filter(Product.id == batch.product_id).first()
        if product:
            stocks = db.query(Stock).filter(Stock.batch_id == batch.id, Stock.quantity > 0).all()
            location_names = []
            for s in stocks:
                loc = db.query(StockLocation).filter(StockLocation.id == s.location_id).first()
                if loc:
                    location_names.append(loc.name)
            result.append({
                "product_name": product.name,
                "code": product.code,
                "expiration_date": batch.expiration_date,
                "quantity": batch.quantity_remaining,
                "locations": ", ".join(location_names) if location_names else "Desconocida"
            })
    return result

def get_low_margin_products(db: Session, margin_threshold: float = 30.0, usd_rate: float = 24.0) -> List[Dict]:
    batches = db.query(ProductBatch).filter(ProductBatch.quantity_remaining > 0).all()
    result = []
    for batch in batches:
        if batch.purchase_price_cup == 0:
            continue
        from services.company_service import get_company_settings
        settings = get_company_settings(db)
        current_usd_rate = settings.usd_rate or 24.0
        current_cost_cup = batch.purchase_price_usd * current_usd_rate
        margin = (batch.sale_price - current_cost_cup) / current_cost_cup * 100
        
        if margin < margin_threshold:
            product = db.query(Product).filter(Product.id == batch.product_id).first()
            if product:
                result.append({
                    "product_name": product.name,
                    "code": product.code,
                    "sale_price": batch.sale_price,
                    "purchase_price": batch.purchase_price_cup,
                    "margin": round(margin, 2),
                    "stock": batch.quantity_remaining
                })
    return result

def export_to_excel(data: List[Dict], filename: str, sheet_name: str = "Reporte"):
    df = pd.DataFrame(data)
    df.to_excel(filename, sheet_name=sheet_name, index=False)
def get_daily_profit(db: Session, start_date: date, end_date: date):
    """
    Retorna la ganancia diaria (ventas - costo) agrupada por día.
    """
    # Ventas diarias
    sales = get_sales_by_period(db, start_date, end_date)
    # Costo de ventas diario (sumando el costo de compra de los productos vendidos)
    # Para simplificar, usamos la tabla Transaction para obtener el costo real
    # Asumiendo que cada venta tiene su costo asociado en la transacción (total es el precio de venta, no costo)
    # Necesitamos obtener el costo desde ProductBatch.purchase_price_cup
    results = db.query(
        func.date(Transaction.created_at).label("day"),
        func.sum(Transaction.quantity * ProductBatch.purchase_price_cup).label("total_cost")
    ).join(ProductBatch, Transaction.batch_id == ProductBatch.id)\
     .filter(Transaction.type == "sale",
             Transaction.created_at >= start_date,
             Transaction.created_at <= end_date)\
     .group_by(func.date(Transaction.created_at))\
     .order_by("day").all()
    
    cost_dict = {r.day: r.total_cost for r in results}
    
    profit_data = []
    for sale in sales:
        day = sale["day"]
        total_sales = sale["total"]
        total_cost = cost_dict.get(day, 0)
        profit = total_sales - total_cost
        profit_data.append({
            "day": day,
            "sales": total_sales,
            "cost": total_cost,
            "profit": profit
        })
    return profit_data