import csv
from datetime import datetime
from sqlalchemy.orm import Session
from services.cash_service import add_cash_movement, get_or_create_cash_register
from models.user import User

def import_cash_movements_from_csv(db: Session, filepath: str, target_cash_register_name: str, user_id: int):
    """Importa movimientos de caja desde archivo CSV (generado por una caja secundaria).
    Los crea en la caja principal asociados a la caja secundaria (se puede usar el nombre de la caja como referencia)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        movements = list(reader)
    
    # Buscar o crear registro de caja secundaria en la BD principal (para asociar movimientos)
    # Usamos el nombre del archivo o pedimos al usuario que indique el nombre de la caja.
    # Por simplicidad, pediremos nombre en el diálogo.
    # Aquí asumimos que target_cash_register_name es el nombre de la caja secundaria.
    secondary_register = get_or_create_cash_register(db, target_cash_register_name, is_main=False)
    
    imported = 0
    for row in movements:
        # Convertir fecha
        mov_date = datetime.strptime(row['fecha'], '%Y-%m-%d %H:%M:%S')
        # Buscar usuario por nombre (si existe en BD principal)
        user = db.query(User).filter(User.username == row['usuario']).first()
        if not user:
            user = db.query(User).filter(User.id == user_id).first()  # fallback al usuario actual
        add_cash_movement(
            db=db,
            cash_register_id=secondary_register.id,
            user_id=user.id,
            movement_type=row['tipo'],
            amount=float(row['monto']),
            currency=row['moneda'],
            description=row['descripcion'],
            reference_id=int(row['referencia']) if row['referencia'] else None
        )
        imported += 1
    db.commit()
    return imported