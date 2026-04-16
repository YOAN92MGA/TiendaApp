from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class CashMovement(Base):
    __tablename__ = "cash_movements"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=False)
    type = Column(String, nullable=False)  # 'sale', 'transfer', 'withdrawal', 'expense', 'currency_purchase', 'zelle_purchase', 'remittance'
    amount = Column(Float, nullable=False)  # monto en la moneda correspondiente
    currency = Column(String, default="CUP")  # CUP, USD, EUR
    reference_id = Column(Integer, nullable=True)  # opcional: ID de venta, etc.
    description = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    # Relaciones (opcional)
    user = relationship("User")
    register = relationship("CashRegister", back_populates="movements")