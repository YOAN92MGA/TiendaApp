from sqlalchemy.orm import Session
from models.expense import Expense
from datetime import datetime, date
from typing import List, Optional

def create_expense(db: Session, description: str, amount: float, source: str, user_id: int) -> Expense:
    """Registra un nuevo gasto."""
    expense = Expense(
        description=description,
        amount=amount,
        source=source,
        user_id=user_id,
        date=datetime.utcnow()
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

def get_expenses(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None, source: Optional[str] = None) -> List[Expense]:
    """Obtiene gastos con filtros opcionales."""
    query = db.query(Expense)
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)
    if source:
        query = query.filter(Expense.source == source)
    return query.order_by(Expense.date.desc()).all()

def delete_expense(db: Session, expense_id: int) -> bool:
    """Elimina un gasto (solo admin)."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        db.delete(expense)
        db.commit()
        return True
    return False