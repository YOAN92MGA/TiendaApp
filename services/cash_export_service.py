import csv
from datetime import date, timedelta
from sqlalchemy.orm import Session
from models.cash_movement import CashMovement
from models.user import User

def export_cash_movements_to_csv(db: Session, filepath: str, cash_register_id: int, target_date: date = None):
    if target_date is None:
        target_date = date.today()
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    movements = db.query(CashMovement).filter(
        CashMovement.cash_register_id == cash_register_id,
        CashMovement.created_at >= start,
        CashMovement.created_at <= end
    ).all()
    
    data = []
    for mov in movements:
        user = db.query(User).filter(User.id == mov.user_id).first()
        data.append({
            'fecha': mov.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': mov.type,
            'monto': mov.amount,
            'moneda': mov.currency,
            'descripcion': mov.description,
            'usuario': user.username if user else '',
            'referencia': mov.reference_id or ''
        })
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['fecha','tipo','monto','moneda','descripcion','usuario','referencia'])
        writer.writeheader()
        writer.writerows(data)
    return len(data)