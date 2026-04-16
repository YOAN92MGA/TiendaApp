from sqlalchemy import Column, Integer, Float, ForeignKey
from config.database import Base

class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)  # precio unitario de venta