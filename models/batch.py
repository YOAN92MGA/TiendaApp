from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    purchase_price_cup = Column(Float, nullable=False)
    purchase_price_usd = Column(Float, nullable=False)
    usd_rate = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=False)
    expiration_date = Column(Date, nullable=False)
    supplier = Column(String, nullable=False)
    quantity_received = Column(Integer, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación con Product (esto es lo que faltaba)
    product = relationship("Product", backref="batches")