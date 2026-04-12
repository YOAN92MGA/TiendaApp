from sqlalchemy.orm import Session
from models.user import User
from utils.security import hash_password, verify_password
from typing import List, Optional

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_all_users(db: Session) -> List[User]:
    return db.query(User).all()

def create_user(db: Session, username: str, password: str, role: str = "employee") -> User:
    hashed = hash_password(password)
    user = User(username=username, password=hashed, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_role(db: Session, user_id: int, new_role: str) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.role = new_role
        db.commit()
        return True
    return False

def update_user_password(db: Session, user_id: int, new_password: str) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.password = hash_password(new_password)
        db.commit()
        return True
    return False

def delete_user(db: Session, user_id: int) -> bool:
    # Evitar eliminar al último administrador
    admin_count = db.query(User).filter(User.role == "admin").count()
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role == "admin" and admin_count <= 1:
        raise Exception("No se puede eliminar el único administrador.")
    if user:
        db.delete(user)
        db.commit()
        return True
    return False