from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from config.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    source = Column(String, nullable=False)  # 'cash_box' o 'fund'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)