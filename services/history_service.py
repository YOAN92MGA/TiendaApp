from sqlalchemy.orm import Session
from models.transaction import Transaction
from models.batch import ProductBatch
from models.product import Product
from models.user import User
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

def get_transaction_types(db: Session) -> List[str]:
    types = db.query(Transaction.type).distinct().all()
    return [t[0] for t in types]

def get_all_users(db: Session) -> List[User]:
    return db.query(User).all()

def get_transactions(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transaction_type: Optional[str] = None,
    user_id: Optional[int] = None
) -> List[Dict]:
    query = db.query(Transaction)
    
    if start_date:
        query = query.filter(Transaction.created_at >= start_date)  # cambiado
    if end_date:
        end_date_plus = end_date + timedelta(days=1)
        query = query.filter(Transaction.created_at < end_date_plus)  # cambiado
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    if user_id:
        query = query.filter(Transaction.user_id == user_id)
    
    transactions = query.order_by(Transaction.created_at.desc()).all()  # cambiado
    
    result = []
    for trans in transactions:
        # Obtener producto a través del batch
        product_name = "N/A"
        product_code = "N/A"
        if trans.batch_id:
            batch = db.query(ProductBatch).filter(ProductBatch.id == trans.batch_id).first()
            if batch and batch.product:
                product_name = batch.product.name
                product_code = batch.product.code
        
        user = db.query(User).filter(User.id == trans.user_id).first()
        
        # Calcular precio unitario (si quantity > 0)
        unit_price = trans.total / trans.quantity if trans.quantity else 0
        
        result.append({
            "id": trans.id,
            "date": trans.created_at,  # usar created_at
            "type": trans.type,
            "product_name": product_name,
            "product_code": product_code,
            "quantity": trans.quantity,
            "price": unit_price,  # calculado
            "from_location": "",  # no existe en Transaction
            "to_location": "",    # no existe en Transaction
            "user": user.username if user else "Desconocido",
            "notes": ""           # no existe en Transaction
        })
    return result