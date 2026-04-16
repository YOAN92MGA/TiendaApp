# services/cash_service.py
from sqlalchemy.orm import Session
from models.cash_register import CashRegister
from models.cash_movement import CashMovement
from models.cash_close import CashClose
from models.expense import Expense
from datetime import date, datetime, timedelta
from typing import Optional, List

# ------------------------------------------------------------
# Registros y caja principal
# ------------------------------------------------------------
def get_or_create_main_register(db: Session) -> CashRegister:
    reg = db.query(CashRegister).filter(CashRegister.is_main == True).first()
    if not reg:
        reg = CashRegister(name="Caja Principal", is_main=True)
        db.add(reg)
        db.commit()
        db.refresh(reg)
    return reg

def get_or_create_cash_register(db: Session) -> CashRegister:
    """Alias para obtener la caja principal (usado por product_service)"""
    return get_or_create_main_register(db)

def get_registers(db: Session) -> List[CashRegister]:
    return db.query(CashRegister).all()

# ------------------------------------------------------------
# Movimientos genéricos
# ------------------------------------------------------------
def add_movement(
    db: Session,
    register_id: int,
    movement_type: str,
    amount: float,
    currency: str = "CUP",
    description: str = "",
    reference_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> CashMovement:
    mov = CashMovement(
        register_id=register_id,
        user_id=user_id,
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

def add_cash_movement(
    db: Session,
    register_id: int,
    movement_type: str,
    amount: float,
    currency: str = "CUP",
    description: str = "",
    reference_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> CashMovement:
    """Alias para add_movement (usado por product_service)"""
    return add_movement(db, register_id, movement_type, amount, currency, description, reference_id, user_id)

# ------------------------------------------------------------
# Consulta de movimientos
# ------------------------------------------------------------
def get_movements_by_register(
    db: Session,
    register_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[CashMovement]:
    query = db.query(CashMovement).filter(CashMovement.register_id == register_id)
    if start_date:
        query = query.filter(CashMovement.date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(CashMovement.date <= datetime.combine(end_date, datetime.max.time()))
    return query.order_by(CashMovement.date.desc()).all()

def get_daily_movements(db: Session, register_id: int, target_date: Optional[date] = None) -> List[CashMovement]:
    if target_date is None:
        target_date = date.today()
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())
    return db.query(CashMovement).filter(
        CashMovement.register_id == register_id,
        CashMovement.date >= start,
        CashMovement.date < end
    ).all()

# ------------------------------------------------------------
# Cálculo de totales y efectivo esperado
# ------------------------------------------------------------
def calculate_daily_totals(db: Session, register_id: int, target_date: Optional[date] = None) -> dict:
    movements = get_daily_movements(db, register_id, target_date)
    totals = {
        'total_sales': sum(m.amount for m in movements if m.type == 'sale' and m.currency == 'CUP'),
        'total_transfers': sum(m.amount for m in movements if m.type == 'transfer'),
        'transfer_count': sum(1 for m in movements if m.type == 'transfer'),
        'total_extractions': sum(m.amount for m in movements if m.type == 'withdrawal'),
        'total_expenses': sum(m.amount for m in movements if m.type == 'expense'),
        'usd_purchased': sum(m.amount for m in movements if m.type == 'currency_purchase' and m.currency == 'USD'),
        'eur_purchased': sum(m.amount for m in movements if m.type == 'currency_purchase' and m.currency == 'EUR'),
        'zelle_purchases': sum(m.amount for m in movements if m.type == 'zelle_purchase'),
        'remittances': sum(m.amount for m in movements if m.type == 'remittance')
    }
    return totals

def get_cash_expected(db: Session, register_id: int, target_date: Optional[date] = None) -> float:
    totals = calculate_daily_totals(db, register_id, target_date)
    expected = totals['total_sales'] - totals['total_extractions'] - totals['total_expenses'] + totals['remittances']
    return max(expected, 0.0)

# ------------------------------------------------------------
# Registro de movimientos específicos (con creación de gastos)
# ------------------------------------------------------------
def register_withdrawal(db: Session, register_id: int, amount: float, reason: str, user_id: int) -> Expense:
    add_movement(db, register_id, "withdrawal", amount, "CUP", reason, user_id=user_id)
    expense = Expense(
        description=f"Extracción de caja: {reason}",
        amount=amount,
        source="caja",
        user_id=user_id
    )
    db.add(expense)
    db.commit()
    return expense

def register_expense(db: Session, register_id: int, amount: float, reason: str, user_id: int) -> Expense:
    add_movement(db, register_id, "expense", amount, "CUP", reason, user_id=user_id)
    expense = Expense(
        description=f"Gasto en efectivo: {reason}",
        amount=amount,
        source="caja",
        user_id=user_id
    )
    db.add(expense)
    db.commit()
    return expense

def register_currency_purchase(db: Session, register_id: int, currency: str, amount: float, rate: float, user_id: int) -> CashMovement:
    return add_movement(db, register_id, "currency_purchase", amount, currency, f"Compra de {currency} a tasa {rate}", user_id=user_id)

def register_remittance(db: Session, register_id: int, amount: float, description: str, user_id: int) -> CashMovement:
    return add_movement(db, register_id, "remittance", amount, "CUP", description, user_id=user_id)

def register_zelle_purchase(db: Session, register_id: int, amount: float, description: str, user_id: int) -> CashMovement:
    return add_movement(db, register_id, "zelle_purchase", amount, "USD", description, user_id=user_id)

# ------------------------------------------------------------
# Cierre de caja
# ------------------------------------------------------------
def close_cash_register(
    db: Session,
    register_id: int,
    counted_cash: float,
    bill_details: dict,
    notes: str = "",
    user_id: Optional[int] = None
) -> CashClose:
    target_date = date.today()
    totals = calculate_daily_totals(db, register_id, target_date)
    expected = get_cash_expected(db, register_id, target_date)
    difference = counted_cash - expected

    close = CashClose(
        register_id=register_id,
        user_id=user_id,
        total_sales=totals['total_sales'],
        total_transfers=totals['total_transfers'],
        transfer_count=totals['transfer_count'],
        total_cash=counted_cash,
        total_extractions=totals['total_extractions'],
        total_expenses=totals['total_expenses'],
        usd_purchased=totals['usd_purchased'],
        eur_purchased=totals['eur_purchased'],
        zelle_purchases=totals['zelle_purchases'],
        remittances=totals['remittances'],
        difference=difference,
        notes=notes,
        details=bill_details
    )
    db.add(close)
    db.commit()
    return close