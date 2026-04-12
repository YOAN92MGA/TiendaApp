from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class CashRegister(Base):
    __tablename__ = "cash_registers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    is_main = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación con movimientos (la clase CashMovement está en otro archivo)
    movements = relationship("CashMovement", back_populates="register")