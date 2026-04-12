from sqlalchemy.orm import Session
from datetime import date, timedelta
from models.batch import ProductBatch
from models.product import Product

def get_expiring_products(db: Session, days: int = 15):
    """Productos proximos a vencer (usando quantity_remaining)"""
    today = date.today()
    limit = today + timedelta(days=days)
    results = db.query(Product.name, Product.code, ProductBatch.expiration_date, ProductBatch.quantity_remaining)\
                .join(ProductBatch, Product.id == ProductBatch.product_id)\
                .filter(ProductBatch.expiration_date <= limit,
                        ProductBatch.expiration_date >= today,
                        ProductBatch.quantity_remaining > 0)\
                .all()
    return [{'product_name': r[0], 'code': r[1], 'expiration_date': r[2], 'quantity': r[3]} for r in results]


def get_low_margin_products(db: Session, threshold: float = 10.0):
    """Productos con margen bajo (< threshold%) usando purchase_price_cup como costo"""
    results = []
    # Obtener lotes con stock > 0
    batches = db.query(ProductBatch).filter(ProductBatch.quantity_remaining > 0).all()

    # Agrupar por producto
    product_data = {}
    for batch in batches:
        prod_id = batch.product_id
        sale_price = batch.sale_price
        cost_price = batch.purchase_price_cup
        if not sale_price or sale_price <= 0:
            continue
        qty = batch.quantity_remaining
        if qty <= 0:
            continue

        if prod_id not in product_data:
            product_data[prod_id] = {
                'total_sales_value': 0,
                'total_cost_value': 0,
                'total_qty': 0,
                'product': None
            }
        product_data[prod_id]['total_sales_value'] += sale_price * qty
        product_data[prod_id]['total_cost_value'] += cost_price * qty
        product_data[prod_id]['total_qty'] += qty

    # Obtener objetos Product
    product_ids = list(product_data.keys())
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    for prod_id, data in product_data.items():
        prod = product_map.get(prod_id)
        if not prod:
            continue
        total_sales = data['total_sales_value']
        total_cost = data['total_cost_value']
        if total_sales <= 0:
            continue
        avg_sale_price = total_sales / data['total_qty']
        avg_cost = total_cost / data['total_qty']
        margin = (avg_sale_price - avg_cost) / avg_sale_price * 100
        if margin < threshold:
            results.append({
                'product_name': prod.name,
                'code': prod.code,
                'margin': round(margin, 2),
                'sale_price': round(avg_sale_price, 2),
                'avg_cost': round(avg_cost, 2)
            })
    return results


def get_startup_notifications(db: Session, expiring_days: int = 15, margin_threshold: float = 10.0):
    """Retorna ambas listas de notificaciones"""
    expiring = get_expiring_products(db, expiring_days)
    low_margin = get_low_margin_products(db, margin_threshold)
    return {
        'expiring_products': expiring,
        'low_margin_products': low_margin
    }