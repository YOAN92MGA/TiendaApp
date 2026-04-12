from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from config.database import Base

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    payment_method = Column(String, nullable=False)  # 'cash', 'zelle', 'transfer'
    total = Column(Float, nullable=False)
    change_given = Column(Float, default=0.0)
    receipt_printed = Column(Integer, default=0)  # booleano
    created_at = Column(DateTime, default=datetime.utcnow)