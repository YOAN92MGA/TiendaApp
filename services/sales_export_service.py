import csv
from datetime import date
from sqlalchemy.orm import Session
from models.transaction import Transaction
from models.batch import ProductBatch
from models.product import Product

def export_sales_to_csv(db: Session, filepath: str, target_date: date = None):
    """Exporta las ventas de una fecha específica (por defecto hoy)."""
    if target_date is None:
        target_date = date.today()
    
    # Obtener transacciones de tipo 'sale' en esa fecha
    sales = db.query(Transaction).filter(
        Transaction.type == 'sale',
        Transaction.created_at >= target_date,
        Transaction.created_at < target_date + timedelta(days=1)
    ).all()
    
    data = []
    for trans in sales:
        batch = db.query(ProductBatch).filter(ProductBatch.id == trans.batch_id).first()
        product = db.query(Product).filter(Product.id == batch.product_id).first() if batch else None
        data.append({
            'fecha': trans.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'codigo_producto': product.code if product else '',
            'producto': product.name if product else '',
            'cantidad': trans.quantity,
            'precio_unitario': trans.total / trans.quantity if trans.quantity else 0,
            'total': trans.total,
            'metodo_pago': '',  # No se almacena en Transaction, podrías obtenerlo de Sale si es necesario
            'usuario_id': trans.user_id
        })
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['fecha', 'codigo_producto', 'producto', 'cantidad', 'precio_unitario', 'total', 'metodo_pago', 'usuario_id'])
        writer.writeheader()
        writer.writerows(data)
    return len(data)