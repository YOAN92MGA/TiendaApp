import csv
import json
from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.stock_location import StockLocation
from datetime import date, datetime

def export_inventory_to_csv(db: Session, filepath: str):
    """Exporta productos disponibles en 'Piso' a un archivo CSV."""
    piso = db.query(StockLocation).filter(StockLocation.name == "Piso").first()
    if not piso:
        raise Exception("Ubicación 'Piso' no encontrada")
    
    stocks = db.query(Stock, ProductBatch, Product).join(
        ProductBatch, Stock.batch_id == ProductBatch.id
    ).join(Product, ProductBatch.product_id == Product.id).filter(
        Stock.location_id == piso.id,
        Stock.quantity > 0
    ).all()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['codigo', 'producto', 'cantidad', 'precio_venta', 'lote_id'])
        for stock, batch, product in stocks:
            writer.writerow([product.code, product.name, stock.quantity, batch.sale_price, batch.id])
    return True

def import_inventory_from_csv(db: Session, filepath: str):
    """Reemplaza el stock local (Piso) con los datos del archivo.
    Útil para máquinas secundarias."""
    piso = db.query(StockLocation).filter(StockLocation.name == "Piso").first()
    if not piso:
        raise Exception("Ubicación 'Piso' no encontrada")
    
    # Leer CSV
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        inventory = list(reader)
    
    # Limpiar stock actual en Piso (solo para esta máquina)
    db.query(Stock).filter(Stock.location_id == piso.id).delete()
    
    # Insertar nuevo stock (asumiendo que los lotes ya existen en la BD local)
    for item in inventory:
        batch_id = int(item['lote_id'])
        quantity = int(item['cantidad'])
        # Verificar si el lote existe en esta BD local
        batch = db.query(ProductBatch).filter(ProductBatch.id == batch_id).first()
        if batch:
            stock = Stock(batch_id=batch_id, location_id=piso.id, quantity=quantity)
            db.add(stock)
    db.commit()
    return True
def export_movements_to_csv(db: Session, register_id: int, filepath: str, start_date: date, end_date: date):
    movements = get_movements_by_register(db, register_id, start_date, end_date)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['fecha', 'tipo', 'monto', 'moneda', 'descripcion', 'referencia'])
        for mov in movements:
            writer.writerow([mov.created_at.strftime('%Y-%m-%d %H:%M:%S'), mov.type, mov.amount, mov.currency, mov.description, mov.reference_id])
    return True
    
def import_movements_from_csv(db: Session, register_id: int, filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            add_movement(
                db=db,
                register_id=register_id,
                movement_type=row['tipo'],
                amount=float(row['monto']),
                currency=row['moneda'],
                description=row['descripcion'],
                reference_id=int(row['referencia']) if row['referencia'] else None
            )
    return True