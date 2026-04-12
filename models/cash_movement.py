from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class CashMovement(Base):
    __tablename__ = "cash_movements"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=False)
    type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="CUP")
    description = Column(Text, nullable=True)
    reference_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    register = relationship("CashRegister", back_populates="movements")