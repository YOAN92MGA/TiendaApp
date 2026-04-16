from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey, JSON
from datetime import datetime
from config.database import Base

class CashClose(Base):
    __tablename__ = "cash_closes"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_sales = Column(Float, default=0.0)
    total_transfers = Column(Float, default=0.0)
    transfer_count = Column(Integer, default=0)
    total_cash = Column(Float, default=0.0)  # efectivo contado
    total_extractions = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    usd_purchased = Column(Float, default=0.0)
    eur_purchased = Column(Float, default=0.0)
    zelle_purchases = Column(Float, default=0.0)
    remittances = Column(Float, default=0.0)
    difference = Column(Float, default=0.0)
    notes = Column(String, nullable=True)
    details = Column(JSON, nullable=True)  # desglose de billetes