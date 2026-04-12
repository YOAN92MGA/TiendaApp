from sqlalchemy.orm import Session
from models.stock import Stock
from models.stock_location import StockLocation
from models.batch import ProductBatch   # <--- corregido
from models.transaction import Transaction
from models.inventory_count import InventoryCount
from datetime import datetime
from typing import List, Dict

def get_current_stock(db: Session, location_id: int) -> List[Dict]:
    """Obtiene el stock actual de una ubicación (Almacén o Piso)."""
    stocks = db.query(Stock, ProductBatch).join(ProductBatch, Stock.batch_id == ProductBatch.id).filter(
        Stock.location_id == location_id, Stock.quantity > 0
    ).all()
    result = []
    for stock, batch in stocks:
        result.append({
            "stock_id": stock.id,
            "batch_id": batch.id,
            "product_id": batch.product_id,
            "quantity": stock.quantity,
            "sale_price": batch.sale_price,
            "expiration_date": batch.expiration_date
        })
    return result

def apply_adjustment(db: Session, batch_id: int, location_id: int, new_quantity: int, user_id: int, reason: str, adjustment_type: str) -> None:
    """
    Aplica un ajuste de inventario para un lote específico en una ubicación.
    adjustment_type: "positive" (se agrega stock) o "negative" (se reduce).
    new_quantity es la cantidad final deseada.
    """
    stock = db.query(Stock).filter(Stock.batch_id == batch_id, Stock.location_id == location_id).first()
    if not stock:
        if adjustment_type == "positive":
            stock = Stock(batch_id=batch_id, location_id=location_id, quantity=0)
            db.add(stock)
        else:
            raise Exception("No existe stock para ajustar.")
    
    old_quantity = stock.quantity
    difference = new_quantity - old_quantity
    if difference == 0:
        return
    
    stock.quantity = new_quantity
    
    # Registrar transacción de ajuste
    transaction = Transaction(
        type="adjustment",
        to_location_id=location_id,  # usamos to_location_id
        batch_id=batch_id,
        quantity=abs(difference),
        price=0.0,
        user_id=user_id,
        notes=f"Ajuste {adjustment_type}: {reason}. Cantidad anterior: {old_quantity}, nueva: {new_quantity}"
    )
    db.add(transaction)
    db.commit()

def save_inventory_count(db: Session, location_id: int, user_id: int, items: List[Dict], notes: str = "") -> InventoryCount:
    """Guarda un conteo de inventario completo."""
    inventory = InventoryCount(
        location_id=location_id,
        user_id=user_id,
        items=items,
        notes=notes
    )
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory