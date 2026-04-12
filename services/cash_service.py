from sqlalchemy.orm import Session
from models.cash_register import CashRegister
from models.cash_movement import CashMovement
from datetime import date, datetime

def get_or_create_main_register(db: Session) -> CashRegister:
    reg = db.query(CashRegister).filter(CashRegister.is_main == True).first()
    if not reg:
        reg = CashRegister(name="Caja Principal", is_main=True)
        db.add(reg)
        db.commit()
        db.refresh(reg)
    return reg

def get_or_create_cash_register(db: Session) -> CashRegister:
    return get_or_create_main_register(db)

def get_registers(db: Session):
    return db.query(CashRegister).all()

def add_movement(db: Session, register_id: int, movement_type: str, amount: float, currency: str = "CUP", description: str = "", reference_id: int = None):
    mov = CashMovement(
        register_id=register_id,
        type=movement_type,
        amount=amount,
        currency=currency,
        description=description,
        reference_id=reference_id
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov

def add_cash_movement(db: Session, register_id: int, movement_type: str, amount: float, currency: str = "CUP", description: str = "", reference_id: int = None):
    return add_movement(db, register_id, movement_type, amount, currency, description, reference_id)

def get_movements_by_register(db: Session, register_id: int, start_date: date = None, end_date: date = None):
    query = db.query(CashMovement).filter(CashMovement.register_id == register_id)
    if start_date:
        query = query.filter(CashMovement.created_at >= start_date)
    if end_date:
        query = query.filter(CashMovement.created_at <= end_date)
    return query.order_by(CashMovement.created_at.desc()).all()